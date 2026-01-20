from django.db import IntegrityError, transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from nbxsync.models import ZabbixHostInterface
from nbxsync.utils.cfggroup.helpers import is_configgroup_assignment, iter_configgroup_members, build_defaults_from_instance

__all__ = ('handle_postcreate_zabbixhostinterface', 'handle_postsave_zabbixhostinterface', 'handle_predelete_zabbixhostinterface')

DEFAULT_EXCLUDE_FIELDS = {
    'id',
    'pk',
    'interfaceid',
    'assigned_object_id',
    'assigned_object_type',
    'assigned_object',
    'last_sync',
    'last_sync_state',
    'last_sync_message',
    'created',
    'last_updated',
    'custom_field_data',
    'parent',
    'zabbixconfigurationgroup',
    'ip',
}


@receiver(post_save, sender=ZabbixHostInterface)
def handle_postcreate_zabbixhostinterface(sender, instance, created, **kwargs):
    if not created or not is_configgroup_assignment(instance):
        return

    def _create_children():
        for assigned in iter_configgroup_members(instance):
            primary_ip = getattr(assigned.assigned_object, 'primary_ip', None)
            if not primary_ip:
                # print("No primary IP -> skip creating a child")
                continue

            lookup = {
                'zabbixserver': instance.zabbixserver,
                'interface_type': instance.interface_type,
                'type': instance.type,
                'assigned_object_type': assigned.assigned_object_type,
                'assigned_object_id': assigned.assigned_object_id,
            }

            defaults = build_defaults_from_instance(
                instance,
                exclude=DEFAULT_EXCLUDE_FIELDS,
                extra={'ip': primary_ip, 'dns': primary_ip.dns_name, 'useip': instance.useip, 'zabbixconfigurationgroup': instance.assigned_object, 'parent': instance},
            )

            try:
                ZabbixHostInterface.objects.update_or_create(**lookup, defaults=defaults)
            except IntegrityError:
                ZabbixHostInterface.objects.filter(**lookup).update(**defaults)

    transaction.on_commit(_create_children)


@receiver(post_save, sender=ZabbixHostInterface)
def handle_postsave_zabbixhostinterface(sender, instance, created, **kwargs):
    if created or not is_configgroup_assignment(instance):
        return

    def _update_children():
        # Base updates from parent for all children
        base_updates = build_defaults_from_instance(instance, exclude=DEFAULT_EXCLUDE_FIELDS)

        # Children that are still linked to a configgroup
        children = instance.children.exclude(zabbixconfigurationgroup__isnull=True)

        with transaction.atomic():
            for child in children.select_for_update():
                primary_ip = getattr(child.assigned_object, 'primary_ip', None)
                if not primary_ip:
                    # print("No primary IP; skip updating this child (keep existing IP/values)")
                    continue

                updates = dict(base_updates)
                updates['ip'] = primary_ip
                updates['dns'] = primary_ip.dns_name
                updates['useip'] = instance.useip

                ZabbixHostInterface.objects.filter(pk=child.pk).update(**updates)

    transaction.on_commit(_update_children)


@receiver(pre_delete, sender=ZabbixHostInterface)
def handle_predelete_zabbixhostinterface(sender, instance, **kwargs):
    if not is_configgroup_assignment(instance):
        return

    ZabbixHostInterface.objects.filter(parent=instance, zabbixconfigurationgroup=instance.assigned_object).delete()
