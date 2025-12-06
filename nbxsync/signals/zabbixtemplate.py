from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from nbxsync.models import ZabbixTemplate, ZabbixMacro

__all__ = ('handle_deleted_zabbixtemplate',)


@receiver(pre_delete, sender=ZabbixTemplate)
def handle_deleted_zabbixtemplate(sender, instance, **kwargs):
    """
    Fires when an ZabbixTemplate is deleted.
    """

    instance_ct = ContentType.objects.get_for_model(instance)

    # Delete all associated objects
    ZabbixMacro.objects.filter(assigned_object_type=instance_ct, assigned_object_id=instance.id).delete()
