from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from nbxsync.models import ZabbixMacroAssignment
from nbxsync.utils.cfggroup.helpers import is_configgroup_assignment
from nbxsync.worker import propagate_macro_assignment_create, propagate_macro_assignment_update

__all__ = ('handle_postcreate_zabbixmacroassignment', 'handle_postsave_zabbixmacroassignment', 'handle_predelete_zabbixmacroassignment')


@receiver(post_save, sender=ZabbixMacroAssignment)
def handle_postcreate_zabbixmacroassignment(sender, instance, created, **kwargs):
    if not created or not is_configgroup_assignment(instance):
        return

    propagate_macro_assignment_create.delay(instance.pk)


@receiver(post_save, sender=ZabbixMacroAssignment)
def handle_postsave_zabbixmacroassignment(sender, instance, created, **kwargs):
    if created or not is_configgroup_assignment(instance):
        return

    propagate_macro_assignment_update.delay(instance.pk)


@receiver(pre_delete, sender=ZabbixMacroAssignment)
def handle_predelete_zabbixmacroassignment(sender, instance, **kwargs):
    # Kept synchronous: must delete children in the same transaction as the
    # parent to avoid FK constraint violations.
    if not is_configgroup_assignment(instance):
        return

    ZabbixMacroAssignment.objects.filter(parent=instance, zabbixconfigurationgroup=instance.assigned_object).delete()
