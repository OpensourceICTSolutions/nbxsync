from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django_rq import get_queue
from rq import Retry
from virtualization.models import VirtualMachine

from dcim.models import Device, VirtualDeviceContext

from nbxsync.choices.syncsot import SyncSOT
from nbxsync.models import ZabbixHostBinding, ZabbixHostgroupAssignment, ZabbixHostInterface, ZabbixHostInventory, ZabbixMacroAssignment, ZabbixServerAssignment, ZabbixTagAssignment, ZabbixTemplateAssignment
from nbxsync.settings import get_plugin_settings
from nbxsync.utils.host_binding import set_host_binding

__all__ = ('handle_deleted_object',)


@receiver(pre_delete, sender=Device)
@receiver(pre_delete, sender=VirtualMachine)
@receiver(pre_delete, sender=VirtualDeviceContext)
def handle_deleted_object(sender, instance, **kwargs):
    """
    Fires when an object is deleted.
    """

    instance_ct = ContentType.objects.get_for_model(instance)

    pluginsettings = get_plugin_settings()

    # Delete all associated objects
    ZabbixHostInventory.objects.filter(assigned_object_type=instance_ct, assigned_object_id=instance.id).delete()
    ZabbixHostInterface.objects.filter(assigned_object_type=instance_ct, assigned_object_id=instance.id).delete()
    ZabbixTemplateAssignment.objects.filter(assigned_object_type=instance_ct, assigned_object_id=instance.id).delete()
    ZabbixHostgroupAssignment.objects.filter(assigned_object_type=instance_ct, assigned_object_id=instance.id).delete()
    ZabbixTagAssignment.objects.filter(assigned_object_type=instance_ct, assigned_object_id=instance.id).delete()
    ZabbixMacroAssignment.objects.filter(assigned_object_type=instance_ct, assigned_object_id=instance.id).delete()

    host_sot = getattr(pluginsettings.sot, 'host', None)
    if host_sot == SyncSOT.NETBOX:
        bindings = list(
            ZabbixHostBinding.objects.filter(
                assigned_object_type=instance_ct,
                assigned_object_id=instance.pk,
            )
        )
        bound_server_ids = {binding.zabbixserver_id for binding in bindings}
        legacy_assignments = ZabbixServerAssignment.objects.filter(
            assigned_object_type=instance_ct,
            assigned_object_id=instance.pk,
            hostid__isnull=False,
        ).select_related('zabbixserver')
        for assignment in legacy_assignments:
            if assignment.zabbixserver_id in bound_server_ids:
                continue
            binding = set_host_binding(
                instance,
                assignment.zabbixserver,
                int(assignment.hostid),
                hostname=str(instance),
            )
            bindings.append(binding)
            bound_server_ids.add(assignment.zabbixserver_id)

        binding_ids = tuple(sorted(binding.pk for binding in bindings))

        if binding_ids:

            def enqueue_delete():
                queue = get_queue('low')
                queue.enqueue_job(
                    queue.create_job(
                        func='nbxsync.worker.deletehost',
                        args=[binding_ids],
                        timeout=9000,
                        retry=Retry(max=5, interval=[60, 300, 900, 3600, 21600]),
                    )
                )

            transaction.on_commit(enqueue_delete)

    # If Zabbix is the SOT, dont delete it from Zabbix, but do delete the ServerAssignment
    if host_sot == SyncSOT.ZABBIX:
        ZabbixServerAssignment.objects.filter(assigned_object_type=instance_ct, assigned_object_id=instance.id).delete()
