from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from nbxsync.models import ZabbixTemplateAssignment
from nbxsync.utils.cfggroup.helpers import is_configgroup_assignment
from nbxsync.worker import propagate_template_assignment, delete_template_assignment_clones

__all__ = ('handle_postsave_zabbixtemplateassignment', 'handle_postdelete_zabbixtemplateassignment')


@receiver(post_save, sender=ZabbixTemplateAssignment)
def handle_postsave_zabbixtemplateassignment(sender, instance, **kwargs):
    if not is_configgroup_assignment(instance):
        return

    propagate_template_assignment.delay(instance.pk)


@receiver(post_delete, sender=ZabbixTemplateAssignment)
def handle_postdelete_zabbixtemplateassignment(sender, instance, **kwargs):
    if not is_configgroup_assignment(instance):
        return

    delete_template_assignment_clones.delay(configgroup_pk=instance.assigned_object_id, assigned_object_type_pk=instance.assigned_object_type_id, zabbixtemplate_pk=instance.zabbixtemplate_id)
