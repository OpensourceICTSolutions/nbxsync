from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from nbxsync.models import ZabbixHostgroupAssignment
from nbxsync.utils.cfggroup.helpers import is_configgroup_assignment
from nbxsync.worker import propagate_hostgroup_assignment, delete_hostgroup_assignment_clones

__all__ = ('handle_postcreate_zabbixhostgroupassignment', 'handle_postsave_zabbixhostgroupassignment', 'handle_postdelete_zabbixhostgroupassignment')


@receiver(post_save, sender=ZabbixHostgroupAssignment)
def handle_postcreate_zabbixhostgroupassignment(sender, instance, created, **kwargs):
    if not created:
        return
    if not is_configgroup_assignment(instance):
        return

    propagate_hostgroup_assignment.delay(instance.pk)


@receiver(post_save, sender=ZabbixHostgroupAssignment)
def handle_postsave_zabbixhostgroupassignment(sender, instance, created, **kwargs):
    if created:
        return
    if not is_configgroup_assignment(instance):
        return

    propagate_hostgroup_assignment.delay(instance.pk)


@receiver(post_delete, sender=ZabbixHostgroupAssignment)
def handle_postdelete_zabbixhostgroupassignment(sender, instance, **kwargs):
    if not is_configgroup_assignment(instance):
        return

    delete_hostgroup_assignment_clones.delay(configgroup_pk=instance.assigned_object_id)
