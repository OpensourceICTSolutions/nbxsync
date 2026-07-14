#!/usr/bin/env python3
"""
SDT (Scheduled Down Time) management command for NetBox + nbxSync.

Creates per-device Zabbix maintenance windows triggered by NetBox native tags.
Uses native Zabbix maintenance with hostgroup scope + tag selector (nb_id)
to narrow to a single device — no hostid resolution needed.

HOW IT WORKS
============
1. Operator adds NetBox native tag: sdt_2h, sdt_4h, sdt_8h, or sdt_24h
2. This command (cron every 15min) creates:
   - ZabbixMaintenance (automatic=True, one-time, correct duration)
   - ZabbixMaintenancePeriod (one-time, starts now)
   - ZabbixMaintenanceObjectAssignment (device's hostgroup)
   - ZabbixMaintenanceTagAssignment (nb_id Equals <device_id>)
   → Zabbix maintenance scoped to the hostgroup but filtered to just this device
3. NetBox tag is REMOVED (it was just a trigger)
4. When active_till passes: Zabbix auto-expires → next run deletes it

USAGE
=====
  */15 * * * * /opt/netbox/venv/bin/python3 /opt/netbox/netbox/manage.py sdt_process
  python manage.py sdt_process --dry-run
"""
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from django_rq import get_queue

from dcim.models import Device
from virtualization.models import VirtualMachine
from nbxsync.models import (
    ZabbixServer, ZabbixMaintenance, ZabbixMaintenancePeriod,
    ZabbixMaintenanceObjectAssignment, ZabbixMaintenanceTagAssignment,
    ZabbixHostgroup, ZabbixTag,
)
from nbxsync.utils import get_assigned_zabbixobjects
from nbxsync.choices import (
    ZabbixMaintenanceTypeChoices as MT,
    ZabbixMaintenanceTagsEvalChoices as TE,
    ZabbixTimePeriodTypeChoices as TP,
    ZabbixMaintenanceTagOperatorChoices as TO,
)

SDT_DURATIONS = {
    'sdt_2h': timedelta(hours=2),
    'sdt_4h': timedelta(hours=4),
    'sdt_8h': timedelta(hours=8),
    'sdt_24h': timedelta(hours=24),
}


class Command(BaseCommand):
    help = 'Process SDT tags → create/remove Zabbix maintenance windows'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry = options.get('dry_run', False)
        now = datetime.now()
        if dry:
            self.stdout.write(self.style.WARNING('=== DRY RUN ===\n'))
        self.stdout.write(f'SDT processing at {now.isoformat()}\n')

        created = 0
        skipped = 0
        hg_ct = ContentType.objects.get_for_model(ZabbixHostgroup)

        # Phase 1: Create maintenance for new sdt_* tags
        self.stdout.write('\n--- Phase 1: Processing SDT tags ---\n')
        for tag_name, duration in SDT_DURATIONS.items():
            for model, label in [(Device, 'device'), (VirtualMachine, 'vm')]:
                ct = ContentType.objects.get_for_model(model)
                for obj in model.objects.filter(tags__name=tag_name):
                    # Check if active SDT already exists for this object
                    existing = ZabbixMaintenance.objects.filter(
                        automatic=True,
                        active_till__gt=now,
                        zabbixmaintenanceobjectassignment__assigned_object_type=ct,
                        zabbixmaintenanceobjectassignment__assigned_object_id=obj.id,
                    ).exists()
                    if existing:
                        skipped += 1
                        continue

                    # Resolve hostgroups that have a groupid (synced to Zabbix)
                    all_objects = get_assigned_zabbixobjects(obj)
                    hgs_with_gid = []
                    for hga in all_objects.get('hostgroups', []):
                        hg = hga.zabbixhostgroup
                        if hg.groupid:
                            hgs_with_gid.append(hg)
                    if not hgs_with_gid:
                        self.stdout.write(self.style.WARNING(
                            f'  SKIP: {obj.name} — no synced hostgroup'))
                        skipped += 1
                        continue

                    # Use the first available hostgroup
                    hg = hgs_with_gid[0]
                    end_time = now + duration
                    seconds_of_day = now.hour * 3600 + now.minute * 60 + now.second
                    dur_secs = int(duration.total_seconds())
                    mw_name = f'[SDT] {obj.name} ({tag_name})'

                    if dry:
                        self.stdout.write(f'  WOULD: {mw_name}')
                        self.stdout.write(f'    HG={hg.name}({hg.groupid}) '
                                          f'tag=nb_id Equals {obj.id}')
                        self.stdout.write(f'    {now} → {end_time} ({duration})')
                        created += 1
                        continue

                    # Create the maintenance
                    server = hg.zabbixserver
                    mw = ZabbixMaintenance.objects.create(
                        name=mw_name, zabbixserver=server,
                        active_since=now, active_till=end_time,
                        description=f'SDT: {tag_name}. Hostgroup: {hg.name}. '
                                    f'Filtered by nb_id={obj.id}.',
                        maintenance_type=MT.WITH_COLLECTION,
                        tags_evaltype=TE.AND_OR, automatic=True)

                    ZabbixMaintenancePeriod.objects.create(
                        zabbixmaintenance=mw,
                        timeperiod_type=TP.ONE_TIME,
                        start_date=now.date(),
                        start_time=seconds_of_day, period=dur_secs)

                    # Scope to hostgroup
                    ZabbixMaintenanceObjectAssignment.objects.create(
                        zabbixmaintenance=mw, assigned_object_type=hg_ct,
                        assigned_object_id=hg.id)

                    # Tag selector: nb_id Equals <device_id> — narrows to 1 host
                    nb_id_tag = ZabbixTag.objects.filter(tag='nb_id').first()
                    if nb_id_tag:
                        ZabbixMaintenanceTagAssignment.objects.create(
                            zabbixmaintenance=mw, zabbixtag=nb_id_tag,
                            operator=TO.EQUALS, value=str(obj.id))

                    # Remove NetBox trigger tag
                    obj.tags.remove(tag_name)
                    obj.save()

                    # Enqueue sync
                    queue = get_queue('low')
                    queue.enqueue_job(queue.create_job(
                        func='nbxsync.worker.syncmaintenance',
                        args=[mw], timeout=9000))

                    self.stdout.write(self.style.SUCCESS(
                        f'  CREATED: {mw_name} → HG={hg.name} '
                        f'nb_id={obj.id} ({duration})'))
                    created += 1

        self.stdout.write(f'\nPhase 1: {created} created, {skipped} skipped\n')

        # Phase 2: Clean up expired maintenance windows
        self.stdout.write('\n--- Phase 2: Cleaning expired SDT ---\n')
        expired = 0
        for mw in ZabbixMaintenance.objects.filter(
            automatic=True, active_till__lt=now
        ):
            name = mw.name
            if dry:
                self.stdout.write(f'  WOULD DELETE: {name}')
                expired += 1
                continue
            mw.delete()
            self.stdout.write(self.style.WARNING(f'  DELETED: {name}'))
            expired += 1

        self.stdout.write(f'\nPhase 2: {expired} expired\n')

        # Summary
        active = ZabbixMaintenance.objects.filter(automatic=True, active_till__gt=now)
        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(f'SDT: {created} created, {skipped} skipped, '
                          f'{expired} expired')
        self.stdout.write(f'Active SDT windows: {active.count()}')
        for mw in active:
            remaining = mw.active_till - now
            self.stdout.write(f'  {mw.name} → {remaining} remaining')
        self.stdout.write(f'{"="*60}\n')
