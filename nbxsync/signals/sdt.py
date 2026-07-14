"""
SDT (Scheduled Down Time) signal handler for nbxSync.

When an operator adds a NetBox native tag sdt_2h/4h/8h/24h to a device or VM,
this signal handler fires immediately and creates a native Zabbix maintenance
window scoped to that specific host — using hostgroup + nb_id tag selector.

This is a native nbxSync feature — no external scripts, no cron, no status changes.

FLOW:
  1. Operator adds tag "sdt_2h" to a VM in NetBox UI
  2. NetBox post_save signal fires → this handler
  3. Handler creates ZabbixMaintenance (automatic=True, 2h duration)
     + ZabbixMaintenancePeriod (one-time, starts now)
     + ZabbixMaintenanceObjectAssignment (device's hostgroup)
     + ZabbixMaintenanceTagAssignment (nb_id Equals <device_id>)
  4. Handler removes the sdt_2h tag (it was just a trigger)
  5. syncmaintenance worker pushes to Zabbix → real maintenance window
  6. After 2h: Zabbix auto-expires the maintenance
  7. Next background sync cycle (60min) cleans up expired automatic maintenances

INSTALLATION:
  Add 'nbxsync.signals.sdt' to the signals __init__.py imports.
"""
import logging
from datetime import datetime, timedelta

from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django_rq import get_queue

from dcim.models import Device
from virtualization.models import VirtualMachine
from nbxsync.models import (
    ZabbixMaintenance,
    ZabbixMaintenancePeriod,
    ZabbixMaintenanceObjectAssignment,
    ZabbixMaintenanceTagAssignment,
    ZabbixHostgroup,
    ZabbixTag,
)
from nbxsync.utils import get_assigned_zabbixobjects
from nbxsync.choices import (
    ZabbixMaintenanceTypeChoices as MT,
    ZabbixMaintenanceTagsEvalChoices as TE,
    ZabbixTimePeriodTypeChoices as TP,
    ZabbixMaintenanceTagOperatorChoices as TO,
)

logger = logging.getLogger(__name__)

# Tag → duration mapping
SDT_DURATIONS = {
    'sdt_2h': timedelta(hours=2),
    'sdt_4h': timedelta(hours=4),
    'sdt_8h': timedelta(hours=8),
    'sdt_24h': timedelta(hours=24),
}

# Track tags before save to detect new tag additions
_SDT_PRE_TAGS = {}


def _get_sdt_tags(obj):
    """Return set of sdt_* tag names on this object."""
    return {t for t in obj.tags.values_list('name', flat=True) if t in SDT_DURATIONS}


def _create_sdt_maintenance(obj, tag_name, duration):
    """Create a Zabbix maintenance window for this object scoped by nb_id tag."""
    now = datetime.now()
    end_time = now + duration
    seconds_of_day = now.hour * 3600 + now.minute * 60 + now.second
    dur_secs = int(duration.total_seconds())

    # Resolve hostgroups that have a groupid (synced to Zabbix)
    all_objects = get_assigned_zabbixobjects(obj)
    hg = None
    for hga in all_objects.get('hostgroups', []):
        if hga.zabbixhostgroup.groupid:
            hg = hga.zabbixhostgroup
            break

    if not hg:
        logger.warning(
            'SDT: %s has %s but no synced hostgroup — skipping',
            obj.name, tag_name)
        return False

    server = hg.zabbixserver
    ct = ContentType.objects.get_for_model(obj)
    hg_ct = ContentType.objects.get_for_model(ZabbixHostgroup)
    mw_name = f'[SDT] {obj.name} ({tag_name})'

    # Check if active SDT already exists
    existing = ZabbixMaintenance.objects.filter(
        automatic=True,
        active_till__gt=now,
        zabbixmaintenanceobjectassignment__assigned_object_type=ct,
        zabbixmaintenanceobjectassignment__assigned_object_id=obj.id,
    ).exists()
    if existing:
        logger.info('SDT: %s already has an active maintenance — skipping', obj.name)
        return False

    # Create maintenance
    mw = ZabbixMaintenance.objects.create(
        name=mw_name,
        zabbixserver=server,
        active_since=now,
        active_till=end_time,
        description=(
            f'Ad-hoc SDT triggered by NetBox tag {tag_name}. '
            f'Scoped to nb_id={obj.id}. Duration: {duration}.'
        ),
        maintenance_type=MT.WITH_COLLECTION,
        tags_evaltype=TE.AND_OR,
        automatic=True,
    )

    # Period: one-time, starts now
    ZabbixMaintenancePeriod.objects.create(
        zabbixmaintenance=mw,
        timeperiod_type=TP.ONE_TIME,
        start_date=now.date(),
        start_time=seconds_of_day,
        period=dur_secs,
    )

    # Scope to the hostgroup
    ZabbixMaintenanceObjectAssignment.objects.create(
        zabbixmaintenance=mw,
        assigned_object_type=hg_ct,
        assigned_object_id=hg.id,
    )

    # Tag selector: nb_id Equals <device_id>
    nb_id_tag = ZabbixTag.objects.filter(tag='nb_id').first()
    if nb_id_tag:
        ZabbixMaintenanceTagAssignment.objects.create(
            zabbixmaintenance=mw,
            zabbixtag=nb_id_tag,
            operator=TO.EQUALS,
            value=str(obj.id),
        )

    # Enqueue sync — pushes maintenance to Zabbix
    queue = get_queue('low')
    queue.enqueue_job(
        queue.create_job(
            func='nbxsync.worker.syncmaintenance',
            args=[mw],
            timeout=9000,
        )
    )

    logger.info(
        'SDT: Created maintenance "%s" for %s (%s, nb_id=%s, hostgroup=%s)',
        mw_name, obj.name, tag_name, obj.id, hg.name,
    )
    return True


@receiver(pre_save, sender=Device)
def device_sdt_pre_save(sender, instance, **kwargs):
    """Track tags before save to detect additions."""
    if instance.pk:
        _SDT_PRE_TAGS[('device', instance.pk)] = _get_sdt_tags(instance)


@receiver(pre_save, sender=VirtualMachine)
def vm_sdt_pre_save(sender, instance, **kwargs):
    """Track tags before save to detect additions."""
    if instance.pk:
        _SDT_PRE_TAGS[('vm', instance.pk)] = _get_sdt_tags(instance)


@receiver(post_save, sender=Device)
def device_sdt_post_save(sender, instance, **kwargs):
    """Check if sdt_* tags were added — create maintenance immediately."""
    if not instance.pk:
        return

    pre_tags = _SDT_PRE_TAGS.pop(('device', instance.pk), set())
    post_tags = _get_sdt_tags(instance)

    # Find newly added sdt_* tags
    new_tags = post_tags - pre_tags
    if not new_tags:
        return

    # Use the longest duration if multiple tags were added
    tag_name = max(new_tags, key=lambda t: SDT_DURATIONS[t])
    duration = SDT_DURATIONS[tag_name]

    created = _create_sdt_maintenance(instance, tag_name, duration)
    if created:
        # Remove all sdt_* tags (they served as triggers)
        for t in new_tags:
            instance.tags.remove(t)
        instance.save()
        logger.info('SDT: Removed trigger tag(s) %s from %s', new_tags, instance.name)


@receiver(post_save, sender=VirtualMachine)
def vm_sdt_post_save(sender, instance, **kwargs):
    """Check if sdt_* tags were added — create maintenance immediately."""
    if not instance.pk:
        return

    pre_tags = _SDT_PRE_TAGS.pop(('vm', instance.pk), set())
    post_tags = _get_sdt_tags(instance)

    new_tags = post_tags - pre_tags
    if not new_tags:
        return

    tag_name = max(new_tags, key=lambda t: SDT_DURATIONS[t])
    duration = SDT_DURATIONS[tag_name]

    created = _create_sdt_maintenance(instance, tag_name, duration)
    if created:
        for t in new_tags:
            instance.tags.remove(t)
        instance.save()
        logger.info('SDT: Removed trigger tag(s) %s from %s', new_tags, instance.name)
