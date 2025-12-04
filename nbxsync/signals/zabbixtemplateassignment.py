from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from nbxsync.models import ZabbixTemplateAssignment
from nbxsync.utils.cfggroup.helpers import is_configgroup_assignment, propagate_group_assignment, delete_group_clones

__all__ = ('handle_postsave_zabbixtemplateassignment', 'handle_postdelete_zabbixtemplateassignment')

DEFAULT_EXCLUDE_TEMPLATE = {
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


@receiver(post_save, sender=ZabbixTemplateAssignment)
def handle_postsave_zabbixtemplateassignment(sender, instance, **kwargs):
    """
    Keep ZabbixTemplateAssignment rows for config group members in sync with the
    config-group-level assignment.

    This replaces both the old "postcreate" and "postsave" handlers, since the
    logic was identical for create and update.
    """
    if not is_configgroup_assignment(instance):
        return

    def lookup_factory(inst, assigned):
        return {
            'zabbixtemplate': inst.zabbixtemplate,
            'assigned_object_type': assigned.assigned_object_type,
            'assigned_object_id': assigned.assigned_object_id,
        }

    propagate_group_assignment(instance=instance, model=ZabbixTemplateAssignment, lookup_factory=lookup_factory, default_exclude=DEFAULT_EXCLUDE_TEMPLATE)


@receiver(post_delete, sender=ZabbixTemplateAssignment)
def handle_postdelete_zabbixtemplateassignment(sender, instance, **kwargs):
    """
    When a config-group-level template assignment is deleted, delete its
    clones for all members of that config group.
    """
    if not is_configgroup_assignment(instance):
        return

    def lookup_factory(inst, assigned):
        return {
            'assigned_object_type': assigned.assigned_object_type,
            'assigned_object_id': assigned.assigned_object_id,
            'zabbixconfigurationgroup': inst.assigned_object,
            'zabbixtemplate': inst.zabbixtemplate,
        }

    delete_group_clones(
        instance=instance,
        model=ZabbixTemplateAssignment,
        lookup_factory=lookup_factory,
    )
