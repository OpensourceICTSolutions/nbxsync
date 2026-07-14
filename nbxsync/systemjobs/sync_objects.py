import logging
from time import monotonic

from django.contrib.contenttypes.models import ContentType
from django_rq import get_queue
from rq.exceptions import NoSuchJobError
from rq.job import Job
from virtualization.models import Cluster, ClusterType, VirtualMachine

from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Platform, Region, Site, SiteGroup
from netbox.jobs import JobRunner, system_job

from nbxsync.models import ZabbixConfigurationGroup, ZabbixServerAssignment
from nbxsync.settings import get_plugin_settings

logger = logging.getLogger(__name__)

_ACTIVE_JOB_STATUSES = {'queued', 'started', 'deferred', 'scheduled'}


def GetSyncInterval():
    pluginsettings = get_plugin_settings()
    return pluginsettings.backgroundsync.objects.interval


def _object_with_descendants_qs(obj, child_attr, manager):
    """Return a queryset of objects matching *child_attr* on obj and its descendants."""
    descendants = obj.get_descendants(include_self=True)
    return manager.filter(**{f'{child_attr}__in': descendants})


def _sync_job_id(content_type, object_id):
    return f'nbxsync-host-{content_type.app_label}-{content_type.model}-{object_id}'


def _job_is_active(queue, job_id):
    try:
        job = Job.fetch(job_id, connection=queue.connection)
    except NoSuchJobError:
        return False

    if job.get_status(refresh=True) in _ACTIVE_JOB_STATUSES:
        return True

    job.delete()
    return False


def _get_eligible_instances(assignment):  # noqa: C901
    """Expand a ZabbixServerAssignment assigned_object into Device/VM instances."""
    obj = assignment.assigned_object
    if obj is None:
        return []

    model = type(obj)

    if model in (Device, VirtualMachine):
        return [obj]

    if model.__name__ == 'VirtualDeviceContext':
        return [obj]

    if model is SiteGroup:
        qs = _object_with_descendants_qs(obj, 'group', Site.objects)
        return list(Device.objects.filter(site__in=qs).distinct()) + list(VirtualMachine.objects.filter(site__in=qs).distinct())

    if model is Site:
        return list(Device.objects.filter(site=obj).distinct()) + list(VirtualMachine.objects.filter(site=obj).distinct())

    if model is Region:
        qs = _object_with_descendants_qs(obj, 'region', Site.objects)
        return list(Device.objects.filter(site__in=qs).distinct()) + list(VirtualMachine.objects.filter(site__in=qs).distinct())

    if model is DeviceRole:
        qs = _object_with_descendants_qs(obj, 'pk', DeviceRole.objects)
        return list(Device.objects.filter(role__in=qs).distinct()) + list(VirtualMachine.objects.filter(role__in=qs).distinct())

    if model is Platform:
        return list(Device.objects.filter(platform=obj).distinct()) + list(VirtualMachine.objects.filter(platform=obj).distinct())

    if model is Manufacturer:
        types = DeviceType.objects.filter(manufacturer=obj)
        return list(Device.objects.filter(device_type__in=types).distinct()) + list(VirtualMachine.objects.filter(platform__manufacturer=obj).distinct())

    if model is DeviceType:
        return list(Device.objects.filter(device_type=obj).distinct())

    if model is Cluster:
        return list(VirtualMachine.objects.filter(cluster=obj).distinct())

    if model is ClusterType:
        return list(VirtualMachine.objects.filter(cluster__type=obj).distinct())

    return []


@system_job(interval=GetSyncInterval())
class SyncObjectsJob(JobRunner):
    class Meta:
        name = 'Zabbix Sync Hosts job'

    def run(self, *args, **kwargs):
        started_at = monotonic()
        queue = None
        enqueued_keys = set()
        assignments_inspected = 0
        hosts_resolved = 0
        hosts_deduplicated = 0
        active_jobs_skipped = 0
        jobs_enqueued = 0
        disabled_scopes = 0

        for assignment in ZabbixServerAssignment.objects.all().select_related('zabbixserver'):
            assignments_inspected += 1
            if isinstance(assignment.assigned_object, ZabbixConfigurationGroup):
                continue

            if not assignment.sync_enabled or not assignment.zabbixserver.sync_enabled:
                disabled_scopes += 1
                continue

            eligible_instances = _get_eligible_instances(assignment)
            hosts_resolved += len(eligible_instances)

            for instance in eligible_instances:
                ct = ContentType.objects.get_for_model(instance)
                key = (ct.app_label, ct.model, instance.pk)
                if key in enqueued_keys:
                    hosts_deduplicated += 1
                    continue
                enqueued_keys.add(key)

                if queue is None:
                    queue = get_queue('low')

                job_id = _sync_job_id(ct, instance.pk)
                if _job_is_active(queue, job_id):
                    active_jobs_skipped += 1
                    continue

                queue.enqueue_job(
                    queue.create_job(
                        func='nbxsync.worker.synchost',
                        args=[ct.app_label, ct.model, instance.pk],
                        timeout=9000,
                        job_id=job_id,
                    )
                )
                jobs_enqueued += 1

        logger.info(
            'Zabbix host reconciliation complete: assignments=%d resolved=%d deduplicated=%d ' 'active_skipped=%d enqueued=%d disabled=%d duration_seconds=%.3f',
            assignments_inspected,
            hosts_resolved,
            hosts_deduplicated,
            active_jobs_skipped,
            jobs_enqueued,
            disabled_scopes,
            monotonic() - started_at,
        )
