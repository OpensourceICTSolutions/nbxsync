from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from nbxsync.models import ZabbixConfigurationGroupAssignment, ZabbixServerAssignment, ZabbixTemplateAssignment, ZabbixTagAssignment, ZabbixHostgroupAssignment, ZabbixMacroAssignment, ZabbixHostInterface
from nbxsync.utils.cfggroup.resync_zabbixconfiggroupassignment import resync_zabbixconfigurationgroupassignment

__all__ = ('handle_postsave_zabbixconfigurationgroupassignment', 'handle_postdelete_zabbixconfigurationgroupassignment')


@receiver(post_save, sender=ZabbixConfigurationGroupAssignment)
def handle_postsave_zabbixconfigurationgroupassignment(sender, instance, created, **kwargs):
    configgroup = instance.zabbixconfigurationgroup
    if configgroup is None:
        return

    resync_zabbixconfigurationgroupassignment(instance)


@receiver(post_delete, sender=ZabbixConfigurationGroupAssignment)
def handle_postdelete_zabbixconfigurationgroupassignment(sender, instance, **kwargs):
    configgroup = instance.zabbixconfigurationgroup
    if configgroup is None:
        return

    assigned_ct = instance.assigned_object_type
    assigned_id = instance.assigned_object_id

    def _delete_children():
        ZabbixServerAssignment.objects.filter(zabbixconfigurationgroup=configgroup, assigned_object_type=assigned_ct, assigned_object_id=assigned_id).delete()
        ZabbixTemplateAssignment.objects.filter(zabbixconfigurationgroup=configgroup, assigned_object_type=assigned_ct, assigned_object_id=assigned_id).delete()
        ZabbixTagAssignment.objects.filter(zabbixconfigurationgroup=configgroup, assigned_object_type=assigned_ct, assigned_object_id=assigned_id).delete()
        ZabbixHostgroupAssignment.objects.filter(zabbixconfigurationgroup=configgroup, assigned_object_type=assigned_ct, assigned_object_id=assigned_id).delete()
        ZabbixMacroAssignment.objects.filter(zabbixconfigurationgroup=configgroup, assigned_object_type=assigned_ct, assigned_object_id=assigned_id).delete()
        ZabbixHostInterface.objects.filter(zabbixconfigurationgroup=configgroup, assigned_object_type=assigned_ct, assigned_object_id=assigned_id).delete()

    transaction.on_commit(_delete_children)
