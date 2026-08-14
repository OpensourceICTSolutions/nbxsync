import logging
from time import monotonic

from django.contrib.contenttypes.models import ContentType
from django_rq import get_queue
from rq.exceptions import NoSuchJobError
from rq.job import Job
from virtualization.models import Cluster, ClusterType, VirtualMachine

from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Platform, Region, Site, SiteGroup, VirtualDeviceContext
from netbox.jobs import JobRunner, system_job

from nbxsync.models import ZabbixConfigurationGroup, ZabbixHostBinding, ZabbixServerAssignment
from nbxsync.settings import get_plugin_settings

logger = logging.getLogger(__name__)

_ACTIVE_JOB_STATUSES = {'queued', 'started', 'deferred', 'scheduled'}
_DEVICE_CT = None
_VM_CT = None
_VDC_CT = None


def GetSyncInterval():
    pluginsettings = get_plugin_settings()
    return pluginsettings.backgroundsync.objects.interval


def _device_ct():
    global _DEVICE_CT
    if _DEVICE_CT is None:
        _DEVICE_CT = ContentType.objects.get_for_model(Device)
    return _DEVICE_CT


def _vm_ct():
    global _VM_CT
    if _VM_CT is None:
        _VM_CT = ContentType.objects.get_for_model(VirtualMachine)
    return _VM_CT


def _vdc_ct():
    global _VDC_CT
    if _VDC_CT is None:
        _VDC_CT = ContentType.objects.get_for_model(VirtualDeviceContext)
    return _VDC_CT


def _object_with_descendants_qs(obj, child_attr, manager):
    """Return a queryset of objects matching *child_attr* on obj and its descendants."""
    if hasattr(obj, 'get_descendants'):
        descendants = obj.get_descendants(include_self=True)
    else:
        descendants = type(obj).objects.filter(pk=obj.pk)
    return manager.filter(**{f'{child_attr}__in': descendants})


def _sync_job_id(app_label, model, object_id):
    return f'nbxsync-host-{app_label}-{model}-{object_id}'


def _job_is_active(queue, job_id):
    """True when a sync for this host is already queued or running.

    Terminal jobs (finished/failed/…) are removed so the deterministic job_id
    can be reused. Failed jobs are logged before deletion so the failure is not
    silently erased from operator-visible history.
    """
    try:
        job = Job.fetch(job_id, connection=queue.connection)
    except NoSuchJobError:
        return False

    status = job.get_status(refresh=True)
    if status in _ACTIVE_JOB_STATUSES:
        return True

    if status == 'failed':
        logger.warning('Replacing failed sync job %s so reconciliation can retry it: %s', job_id, getattr(job, 'exc_info', None) or status)

    job.delete()
    return False


def _add_device_vm_pks(keys, device_qs=None, vm_qs=None):
    """Add (app_label, model, pk) tuples without materialising model instances."""
    if device_qs is not None:
        ct = _device_ct()
        for pk in device_qs.values_list('pk', flat=True).iterator():
            keys.add((ct.app_label, ct.model, pk))
    if vm_qs is not None:
        ct = _vm_ct()
        for pk in vm_qs.values_list('pk', flat=True).iterator():
            keys.add((ct.app_label, ct.model, pk))


def _collect_eligible_keys(assignment, keys):  # noqa: C901
    """Add Device/VM/VDC keys covered by a ZabbixServerAssignment."""
    obj = assignment.assigned_object
    if obj is None:
        return 0

    model = type(obj)
    before = len(keys)

    if model is Device:
        ct = _device_ct()
        keys.add((ct.app_label, ct.model, obj.pk))
    elif model is VirtualMachine:
        ct = _vm_ct()
        keys.add((ct.app_label, ct.model, obj.pk))
    elif model is VirtualDeviceContext:
        ct = _vdc_ct()
        keys.add((ct.app_label, ct.model, obj.pk))
    elif model is SiteGroup:
        sites = _object_with_descendants_qs(obj, 'group', Site.objects)
        _add_device_vm_pks(keys, Device.objects.filter(site__in=sites), VirtualMachine.objects.filter(site__in=sites))
    elif model is Site:
        _add_device_vm_pks(keys, Device.objects.filter(site=obj), VirtualMachine.objects.filter(site=obj))
    elif model is Region:
        sites = _object_with_descendants_qs(obj, 'region', Site.objects)
        _add_device_vm_pks(keys, Device.objects.filter(site__in=sites), VirtualMachine.objects.filter(site__in=sites))
    elif model is DeviceRole:
        roles = _object_with_descendants_qs(obj, 'pk', DeviceRole.objects)
        _add_device_vm_pks(keys, Device.objects.filter(role__in=roles), VirtualMachine.objects.filter(role__in=roles))
    elif model is Platform:
        _add_device_vm_pks(keys, Device.objects.filter(platform=obj), VirtualMachine.objects.filter(platform=obj))
    elif model is Manufacturer:
        types = DeviceType.objects.filter(manufacturer=obj)
        _add_device_vm_pks(keys, Device.objects.filter(device_type__in=types), VirtualMachine.objects.filter(platform__manufacturer=obj))
    elif model is DeviceType:
        _add_device_vm_pks(keys, Device.objects.filter(device_type=obj))
    elif model is Cluster:
        _add_device_vm_pks(keys, vm_qs=VirtualMachine.objects.filter(cluster=obj))
    elif model is ClusterType:
        _add_device_vm_pks(keys, vm_qs=VirtualMachine.objects.filter(cluster__type=obj))

    return len(keys) - before


@system_job(interval=GetSyncInterval())
class SyncObjectsJob(JobRunner):
    class Meta:
        name = 'Zabbix Sync Hosts job'

    def run(self, *args, **kwargs):
        started_at = monotonic()
        queue = None
        keys = set()
        assignments_inspected = 0
        bindings_inspected = 0
        hosts_resolved = 0
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

            hosts_resolved += _collect_eligible_keys(assignment, keys)

        for binding in ZabbixHostBinding.objects.select_related('assigned_object_type').iterator():
            bindings_inspected += 1
            if not binding.assigned_object_type_id or not binding.assigned_object_id:
                continue
            # Orphan bindings (NetBox object already gone) must not enqueue sync jobs.
            model_class = binding.assigned_object_type.model_class()
            if model_class is None or not model_class.objects.filter(pk=binding.assigned_object_id).exists():
                continue
            keys.add((binding.assigned_object_type.app_label, binding.assigned_object_type.model, binding.assigned_object_id))

        hosts_deduplicated = max(0, hosts_resolved + bindings_inspected - len(keys))

        for app_label, model, pk in keys:
            if queue is None:
                queue = get_queue('low')

            job_id = _sync_job_id(app_label, model, pk)
            if _job_is_active(queue, job_id):
                active_jobs_skipped += 1
                continue

            queue.enqueue_job(
                queue.create_job(
                    func='nbxsync.worker.synchost',
                    args=[app_label, model, pk],
                    timeout=9000,
                    job_id=job_id,
                )
            )
            jobs_enqueued += 1

        logger.info(
            'Zabbix host reconciliation complete: assignments=%d bindings=%d resolved=%d deduplicated=%d active_skipped=%d enqueued=%d disabled=%d duration_seconds=%.3f',
            assignments_inspected,
            bindings_inspected,
            hosts_resolved,
            hosts_deduplicated,
            active_jobs_skipped,
            jobs_enqueued,
            disabled_scopes,
            monotonic() - started_at,
        )
