from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from nbxsync.models import ZabbixServerAssignment
from nbxsync.utils.cfggroup.helpers import delete_group_clones, is_configgroup_assignment, propagate_group_assignment

__all__ = ('handle_sync_zabbixserverassignment', 'handle_postdelete_zabbixserverassignment')


DEFAULT_EXCLUDE_SERVER = {
    'id',
    'pk',
    'assigned_object_id',
    'assigned_object_type',
    'assigned_object',
    'last_sync',
    'last_sync_state',
    'last_sync_message',
    'created',
    'last_updated',
    'custom_field_data',
}


@receiver(post_save, sender=ZabbixServerAssignment)
def handle_sync_zabbixserverassignment(sender, instance, **kwargs):
    """
    Runs on both create and update; keeps member assignments in sync
    with the config group-level assignment.
    """
    if not is_configgroup_assignment(instance):
        return

    def lookup_factory(inst, assigned):
        return {
            'zabbixserver': inst.zabbixserver,
            'assigned_object_type': assigned.assigned_object_type,
            'assigned_object_id': assigned.assigned_object_id,
        }

    propagate_group_assignment(
        instance=instance,
        model=ZabbixServerAssignment,
        lookup_factory=lookup_factory,
        default_exclude=DEFAULT_EXCLUDE_SERVER,
    )


@receiver(post_delete, sender=ZabbixServerAssignment)
def handle_postdelete_zabbixserverassignment(sender, instance, **kwargs):
    if not is_configgroup_assignment(instance):
        return

    def lookup_factory(inst, assigned):
        return {
            'assigned_object_type': assigned.assigned_object_type,
            'assigned_object_id': assigned.assigned_object_id,
            'zabbixconfigurationgroup': inst.assigned_object,
            'zabbixserver': inst.zabbixserver,
        }

    delete_group_clones(
        instance=instance,
        model=ZabbixServerAssignment,
        lookup_factory=lookup_factory,
    )
