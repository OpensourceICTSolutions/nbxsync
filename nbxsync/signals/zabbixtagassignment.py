from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from nbxsync.models import ZabbixTagAssignment
from nbxsync.utils.cfggroup.helpers import is_configgroup_assignment
from nbxsync.worker import propagate_tag_assignment, delete_tag_assignment_clones

__all__ = ('handle_sync_zabbixtagassignment', 'handle_postdelete_zabbixtagassignment')


@receiver(post_save, sender=ZabbixTagAssignment)
def handle_sync_zabbixtagassignment(sender, instance, **kwargs):
    if not is_configgroup_assignment(instance):
        return

    propagate_tag_assignment.delay(instance.pk)


@receiver(post_delete, sender=ZabbixTagAssignment)
def handle_postdelete_zabbixtagassignment(sender, instance, **kwargs):
    if not is_configgroup_assignment(instance):
        return

    delete_tag_assignment_clones.delay(configgroup_pk=instance.assigned_object_id, zabbixtag_pk=instance.zabbixtag_id)
