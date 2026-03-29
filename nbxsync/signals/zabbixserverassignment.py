from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from nbxsync.models import ZabbixServerAssignment
from nbxsync.utils.cfggroup.helpers import is_configgroup_assignment
from nbxsync.worker import propagate_server_assignment, delete_server_assignment_clones

__all__ = ('handle_sync_zabbixserverassignment', 'handle_postdelete_zabbixserverassignment')


@receiver(post_save, sender=ZabbixServerAssignment)
def handle_sync_zabbixserverassignment(sender, instance, **kwargs):
    if not is_configgroup_assignment(instance):
        return

    propagate_server_assignment.delay(instance.pk)


@receiver(post_delete, sender=ZabbixServerAssignment)
def handle_postdelete_zabbixserverassignment(sender, instance, **kwargs):
    if not is_configgroup_assignment(instance):
        return

    delete_server_assignment_clones.delay(configgroup_pk=instance.assigned_object_id, assigned_object_type_pk=instance.assigned_object_type_id, zabbixserver_pk=instance.zabbixserver_id)
