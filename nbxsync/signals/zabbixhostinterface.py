from django.db import IntegrityError, transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from nbxsync.models import ZabbixHostInterface
from nbxsync.utils.cfggroup.helpers import delete_group_clones, is_configgroup_assignment, iter_configgroup_members, build_defaults_from_instance

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
            # Set dns_name to None
            # if the 'dns' field is a template, prefer that (more specific)
            dns_name = ''
            if instance.dns_is_template():
                dns_name = instance.dns

            primary_ip = getattr(assigned.assigned_object, 'primary_ip', None)

            # If a primary IP is assigned, and the DNS name is *not* a template
            # then use the DNS Name from the IP
            if primary_ip and not instance.dns_is_template():
                dns_name = primary_ip.dns_name

            extra_fields = {'ip': primary_ip, 'dns': dns_name, 'useip': instance.useip, 'zabbixconfigurationgroup': instance.assigned_object, 'parent': instance}

            if not primary_ip and dns_name == '':
                continue

            lookup = {'zabbixserver': instance.zabbixserver, 'interface_type': instance.interface_type, 'type': instance.type, 'assigned_object_type': assigned.assigned_object_type, 'assigned_object_id': assigned.assigned_object_id}

            defaults = build_defaults_from_instance(instance, exclude=DEFAULT_EXCLUDE_FIELDS, extra=extra_fields)

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
                # Set dns_name to None
                # if the 'dns' field is a template, prefer that (more specific)
                dns_name = ''
                if instance.dns_is_template():
                    dns_name = child.dns

                primary_ip = getattr(child.assigned_object, 'primary_ip', None)

                # If a primary IP is assigned, and the DNS name is *not* a template
                # then use the DNS Name from the IP
                if primary_ip and not instance.dns_is_template():
                    dns_name = primary_ip.dns_name

                if not primary_ip and dns_name == '':
                    continue

                updates = dict(base_updates)
                updates['ip'] = primary_ip
                updates['dns'] = dns_name
                updates['useip'] = instance.useip

                ZabbixHostInterface.objects.filter(pk=child.pk).update(**updates)

    transaction.on_commit(_update_children)


@receiver(pre_delete, sender=ZabbixHostInterface)
def handle_predelete_zabbixhostinterface(sender, instance, **kwargs):
    if not is_configgroup_assignment(instance):
        return

    # ZabbixHostInterface.objects.filter(parent=instance, zabbixconfigurationgroup=instance.assigned_object).delete()

    def lookup_factory(inst, assigned):
        return {
            'assigned_object_type': assigned.assigned_object_type,
            'assigned_object_id': assigned.assigned_object_id,
            'zabbixconfigurationgroup': inst.assigned_object,
            'type': inst.type,
            'useip': inst.useip,
            'interface_type': inst.interface_type,
            'zabbixserver': inst.zabbixserver,
        }

    delete_group_clones(
        instance=instance,
        model=ZabbixHostInterface,
        lookup_factory=lookup_factory,
    )
