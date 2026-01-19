from django.db import transaction

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from nbxsync.models import ZabbixMacroAssignment
from nbxsync.utils.cfggroup.helpers import build_defaults_from_instance, is_configgroup_assignment, propagate_group_assignment


__all__ = ('handle_postcreate_zabbixmacroassignment', 'handle_postsave_zabbixmacroassignment', 'handle_predelete_zabbixmacroassignment')

COMMON_EXCLUDE_MACRO = {
    'id',
    'pk',
    'assigned_object_id',
    'assigned_object_type',
    'assigned_object',
    'created',
    'last_updated',
    'custom_field_data',
    'parent',
}

DEFAULT_EXCLUDE_MACRO_CREATE = COMMON_EXCLUDE_MACRO
DEFAULT_EXCLUDE_MACRO_UPDATE = COMMON_EXCLUDE_MACRO | {
    'last_sync',
    'last_sync_state',
    'last_sync_message',
    'zabbixconfigurationgroup',
}


@receiver(post_save, sender=ZabbixMacroAssignment)
def handle_postcreate_zabbixmacroassignment(sender, instance, created, **kwargs):
    if not created or not is_configgroup_assignment(instance):
        return

    def lookup_factory(inst, assigned):
        return {
            'zabbixmacro': inst.zabbixmacro,
            'is_regex': inst.is_regex,
            'context': inst.context,
            'value': inst.value,
            'assigned_object_type': assigned.assigned_object_type,
            'assigned_object_id': assigned.assigned_object_id,
        }

    propagate_group_assignment(
        instance=instance,
        model=ZabbixMacroAssignment,
        lookup_factory=lookup_factory,
        default_exclude=DEFAULT_EXCLUDE_MACRO_CREATE,
        defaults_extra={'parent': instance},
    )


@receiver(post_save, sender=ZabbixMacroAssignment)
def handle_postsave_zabbixmacroassignment(sender, instance, created, **kwargs):
    if created or not is_configgroup_assignment(instance):
        return

    def _update_children():
        updates = build_defaults_from_instance(
            instance,
            exclude=DEFAULT_EXCLUDE_MACRO_UPDATE,
        )
        instance.children.exclude(zabbixconfigurationgroup__isnull=True).update(**updates)

    transaction.on_commit(_update_children)


@receiver(pre_delete, sender=ZabbixMacroAssignment)
def handle_predelete_zabbixmacroassignment(sender, instance, **kwargs):
    if not is_configgroup_assignment(instance):
        return

    ZabbixMacroAssignment.objects.filter(parent=instance, zabbixconfigurationgroup=instance.assigned_object).delete()
