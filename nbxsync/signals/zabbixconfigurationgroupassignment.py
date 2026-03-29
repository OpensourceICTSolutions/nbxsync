from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from nbxsync.models import ZabbixConfigurationGroupAssignment
from nbxsync.worker import propagate_configgroup_assignment, delete_configgroup_assignment_children

__all__ = ('handle_postsave_zabbixconfigurationgroupassignment', 'handle_postdelete_zabbixconfigurationgroupassignment')


@receiver(post_save, sender=ZabbixConfigurationGroupAssignment)
def handle_postsave_zabbixconfigurationgroupassignment(sender, instance, created, **kwargs):
    if instance.zabbixconfigurationgroup is None:
        return

    propagate_configgroup_assignment.delay(instance.pk)


@receiver(post_delete, sender=ZabbixConfigurationGroupAssignment)
def handle_postdelete_zabbixconfigurationgroupassignment(sender, instance, **kwargs):
    if instance.zabbixconfigurationgroup is None:
        return

    delete_configgroup_assignment_children.delay(configgroup_pk=instance.zabbixconfigurationgroup.pk, assigned_object_type_pk=instance.assigned_object_type_id, assigned_object_id=instance.assigned_object_id)
