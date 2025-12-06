from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, models, transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from nbxsync.models import ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment, ZabbixHostgroupAssignment

__all__ = ('handle_postcreate_zabbixhostgroupassignment', 'handle_postsave_zabbixhostgroupassignment', 'handle_postdelete_zabbixhostgroupassignment')


@receiver(post_save, sender=ZabbixHostgroupAssignment)
def handle_postcreate_zabbixhostgroupassignment(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.assigned_object_type_id != ContentType.objects.get_for_model(ZabbixConfigurationGroup).id:
        return

    def _create_rhs():
        configurationgroup_obj = instance.assigned_object_type.get_object_for_this_type(pk=instance.assigned_object_id)

        default_exclude = {
            'id',
            'pk',
            'groupid',
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

        for assigned in ZabbixConfigurationGroupAssignment.objects.filter(zabbixconfigurationgroup=configurationgroup_obj).select_related('assigned_object_type'):
            lookup = {
                'zabbixhostgroup': instance.zabbixhostgroup,
                'assigned_object_type': assigned.assigned_object_type,
                'assigned_object_id': assigned.assigned_object_id,
            }

            defaults = {
                'zabbixconfigurationgroup': instance.assigned_object,
            }

            # Check if a record exists and has zabbixconfigurationgroup=None, dont touch it
            existing_assignment = ZabbixHostgroupAssignment.objects.filter(**lookup).first()
            if existing_assignment and existing_assignment.zabbixconfigurationgroup is None:
                continue

            for field in instance._meta.concrete_fields:
                name = field.name
                if name in default_exclude or name == 'zabbixconfigurationgroup':
                    continue
                if isinstance(field, models.ForeignKey):
                    defaults[field.attname] = getattr(instance, field.attname)

            try:
                ZabbixHostgroupAssignment.objects.update_or_create(**lookup, defaults=defaults)
            except IntegrityError:
                ZabbixHostgroupAssignment.objects.filter(**lookup).update(**defaults)

    transaction.on_commit(_create_rhs)


@receiver(post_save, sender=ZabbixHostgroupAssignment)
def handle_postsave_zabbixhostgroupassignment(sender, instance, created, **kwargs):
    if created:
        return

    if instance.assigned_object_type_id != ContentType.objects.get_for_model(ZabbixConfigurationGroup).id:
        return

    def _create_rhs():
        configurationgroup_obj = instance.assigned_object_type.get_object_for_this_type(pk=instance.assigned_object_id)

        default_exclude = {
            'id',
            'pk',
            'groupid',
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

        for assigned in ZabbixConfigurationGroupAssignment.objects.filter(zabbixconfigurationgroup=configurationgroup_obj).select_related('assigned_object_type'):
            lookup = {
                'zabbixhostgroup': instance.zabbixhostgroup,
                'assigned_object_type': assigned.assigned_object_type,
                'assigned_object_id': assigned.assigned_object_id,
            }

            defaults = {
                'zabbixconfigurationgroup': instance.assigned_object,
            }

            # Check if a record exists and has zabbixconfigurationgroup=None, dont touch it
            existing_assignment = ZabbixHostgroupAssignment.objects.filter(**lookup).first()
            if existing_assignment and existing_assignment.zabbixconfigurationgroup is None:
                continue

            for field in instance._meta.concrete_fields:
                name = field.name
                if name in default_exclude or name == 'zabbixconfigurationgroup':
                    continue
                if isinstance(field, models.ForeignKey):
                    defaults[field.attname] = getattr(instance, field.attname)

            try:
                ZabbixHostgroupAssignment.objects.update_or_create(**lookup, defaults=defaults)
            except IntegrityError:
                ZabbixHostgroupAssignment.objects.filter(**lookup).update(**defaults)

    transaction.on_commit(_create_rhs)


@receiver(post_delete, sender=ZabbixHostgroupAssignment)
def handle_postdelete_zabbixhostgroupassignment(sender, instance, **kwargs):
    if instance.assigned_object_type_id != ContentType.objects.get_for_model(ZabbixConfigurationGroup).id:
        return

    def _delete_rhs():
        assignments = ZabbixHostgroupAssignment.objects.filter(zabbixconfigurationgroup_id=instance.assigned_object_id).select_related('assigned_object_type')

        for assigned in assignments:
            ZabbixHostgroupAssignment.objects.filter(
                assigned_object_type=assigned.assigned_object_type,
                assigned_object_id=assigned.assigned_object_id,
                zabbixconfigurationgroup=instance.assigned_object,
            ).delete()

    transaction.on_commit(_delete_rhs)
