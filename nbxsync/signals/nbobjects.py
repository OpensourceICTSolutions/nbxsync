from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django_rq import get_queue

from dcim.models import Device
from virtualization.models import VirtualMachine

from nbxsync.choices.syncsot import SyncSOT
from nbxsync.models import ZabbixHostgroupAssignment, ZabbixHostInterface, ZabbixHostInventory, ZabbixMacroAssignment, ZabbixServerAssignment, ZabbixTagAssignment, ZabbixTemplateAssignment
from nbxsync.settings import get_plugin_settings

__all__ = ('handle_deleted_object',)


@receiver(pre_delete, sender=Device)
@receiver(pre_delete, sender=VirtualMachine)
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
    # If the SOT is Netbox, delete the host from Netbox
    if host_sot == SyncSOT.NETBOX:
        queue = get_queue('low')
        queue.enqueue_job(
            queue.create_job(
                func='nbxsync.worker.deletehost',
                args=[instance],
                timeout=9000,
            )
        )

    # If Zabbix is the SOT, dont delete it from Zabbix, but do delete the ServerAssignment
    if host_sot == SyncSOT.ZABBIX:
        ZabbixServerAssignment.objects.filter(assigned_object_type=instance_ct, assigned_object_id=instance.id).delete()
