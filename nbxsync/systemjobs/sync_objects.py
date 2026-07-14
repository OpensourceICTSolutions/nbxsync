from django.contrib.contenttypes.models import ContentType
from django_rq import get_queue
from virtualization.models import Cluster, ClusterType, VirtualMachine

from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Platform, Region, Site, SiteGroup
from netbox.jobs import JobRunner, system_job

from nbxsync.models import ZabbixConfigurationGroup, ZabbixServerAssignment
from nbxsync.settings import get_plugin_settings


def GetSyncInterval():
    pluginsettings = get_plugin_settings()
    return pluginsettings.backgroundsync.objects.interval


def _get_descendants_or_self(obj):
    """Return obj and its descendants using tree API if available, else manual recursion."""
    if hasattr(obj, 'get_descendants'):
        return list(obj.get_descendants(include_self=True))
    result = [obj]
    parent_attr = getattr(obj, 'parent', None)
    while parent_attr is not None:
        if hasattr(parent_attr, 'get_descendants'):
            return result + list(parent_attr.get_descendants(include_self=True))
        result.append(parent_attr)
        parent_attr = getattr(parent_attr, 'parent', None)
    return result


def _object_with_descendants_qs(obj, child_attr, manager):
    """Return a queryset of objects matching *child_attr* on obj and its descendants."""
    descendants = obj.get_descendants(include_self=True)
    return manager.filter(**{f'{child_attr}__in': descendants})


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
        return list(Device.objects.filter(site__in=qs)) + list(VirtualMachine.objects.filter(site__in=qs))

    if model is Site:
        return list(Device.objects.filter(site=obj)) + list(VirtualMachine.objects.filter(site=obj))

    if model is Region:
        qs = _object_with_descendants_qs(obj, 'region', Site.objects)
        return list(Device.objects.filter(site__in=qs)) + list(VirtualMachine.objects.filter(site__in=qs))

    if model is DeviceRole:
        qs = _object_with_descendants_qs(obj, 'pk', DeviceRole.objects)
        return list(Device.objects.filter(role__in=qs)) + list(VirtualMachine.objects.filter(role__in=qs))

    if model is Platform:
        return list(Device.objects.filter(platform=obj)) + list(VirtualMachine.objects.filter(platform=obj))

    if model is Manufacturer:
        types = DeviceType.objects.filter(manufacturer=obj)
        return list(Device.objects.filter(device_type__in=types)) + list(VirtualMachine.objects.filter(platform__manufacturer=obj))

    if model is DeviceType:
        return list(Device.objects.filter(device_type=obj))

    if model is Cluster:
        return list(VirtualMachine.objects.filter(cluster=obj))

    if model is ClusterType:
        return list(VirtualMachine.objects.filter(cluster__type=obj))

    return []


@system_job(interval=GetSyncInterval())
class SyncObjectsJob(JobRunner):
    class Meta:
        name = 'Zabbix Sync Hosts job'

    def run(self, *args, **kwargs):
        queue = get_queue('low')
        enqueued_keys = set()

        for assignment in ZabbixServerAssignment.objects.all().select_related('zabbixserver'):
            if isinstance(assignment.assigned_object, ZabbixConfigurationGroup):
                continue

            if not assignment.sync_enabled or not assignment.zabbixserver.sync_enabled:
                continue

            eligible_instances = _get_eligible_instances(assignment)

            for instance in eligible_instances:
                ct = ContentType.objects.get_for_model(instance)
                key = (ct.app_label, ct.model, instance.pk)
                if key in enqueued_keys:
                    continue
                enqueued_keys.add(key)

                queue.enqueue_job(
                    queue.create_job(
                        func='nbxsync.worker.synchost',
                        args=[instance],
                        timeout=9000,
                    )
                )
