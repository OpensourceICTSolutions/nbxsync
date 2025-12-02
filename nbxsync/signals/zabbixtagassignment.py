from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from nbxsync.models import ZabbixTagAssignment
from nbxsync.utils.cfggroup.helpers import delete_group_clones, is_configgroup_assignment, propagate_group_assignment

__all__ = ('handle_sync_zabbixtagassignment', 'handle_postdelete_zabbixtagassignment')

DEFAULT_EXCLUDE_TAG = {
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


@receiver(post_save, sender=ZabbixTagAssignment)
def handle_sync_zabbixtagassignment(sender, instance, **kwargs):
    if not is_configgroup_assignment(instance):
        return

    def lookup_factory(inst, assigned):
        return {
            'zabbixtag': inst.zabbixtag,
            'assigned_object_type': assigned.assigned_object_type,
            'assigned_object_id': assigned.assigned_object_id,
        }

    propagate_group_assignment(
        instance=instance,
        model=ZabbixTagAssignment,
        lookup_factory=lookup_factory,
        default_exclude=DEFAULT_EXCLUDE_TAG,
    )


@receiver(post_delete, sender=ZabbixTagAssignment)
def handle_postdelete_zabbixtagassignment(sender, instance, **kwargs):
    if not is_configgroup_assignment(instance):
        return

    def lookup_factory(inst, assigned):
        return {
            'zabbixtag': inst.zabbixtag,
            'assigned_object_type': assigned.assigned_object_type,
            'assigned_object_id': assigned.assigned_object_id,
            'zabbixconfigurationgroup': inst.assigned_object,
        }

    delete_group_clones(
        instance=instance,
        model=ZabbixTagAssignment,
        lookup_factory=lookup_factory,
    )
