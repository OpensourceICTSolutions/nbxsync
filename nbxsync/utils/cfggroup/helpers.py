from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, models, transaction

from nbxsync.models import ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment


def get_configgroup_ct_id():
    if not hasattr(get_configgroup_ct_id, '_ct_id'):
        get_configgroup_ct_id._ct_id = ContentType.objects.get_for_model(ZabbixConfigurationGroup).id
    return get_configgroup_ct_id._ct_id


def is_configgroup_assignment(instance):
    return instance.assigned_object_type_id == ContentType.objects.get_for_model(ZabbixConfigurationGroup).id


def iter_configgroup_members(instance):
    configurationgroup_obj = instance.assigned_object
    return ZabbixConfigurationGroupAssignment.objects.filter(zabbixconfigurationgroup=configurationgroup_obj).select_related('assigned_object_type')


def build_defaults_from_instance(instance, *, exclude=frozenset(), extra=None):
    defaults = {}

    for field in instance._meta.concrete_fields:
        name = field.name
        if name in exclude:
            continue

        # Skip reverse relations, etc. Only process normal/concrete fields.
        if isinstance(field, models.ForeignKey):
            # attname is the `<field>_id` column
            defaults[field.attname] = getattr(instance, field.attname)
        else:
            defaults[name] = getattr(instance, name)

    if extra:
        defaults.update(extra)

    return defaults


def propagate_group_assignment(*, instance, model, lookup_factory, default_exclude=frozenset(), defaults_extra=None, respect_existing_null_group_field='zabbixconfigurationgroup'):
    def _do():
        for assigned in iter_configgroup_members(instance):
            lookup = lookup_factory(instance, assigned)

            if respect_existing_null_group_field:
                # Check if a record exists and has group=None; don't touch it.
                existing = model.objects.filter(**lookup).first()
                if existing is not None and getattr(existing, respect_existing_null_group_field) is None:
                    continue

            defaults = build_defaults_from_instance(
                instance,
                exclude=default_exclude | {respect_existing_null_group_field} if respect_existing_null_group_field else default_exclude,
                extra={'zabbixconfigurationgroup': instance.assigned_object, **(defaults_extra or {})},
            )

            try:
                model.objects.update_or_create(**lookup, defaults=defaults)
            except IntegrityError:
                # Race-safe-ish fallback
                model.objects.filter(**lookup).update(**defaults)

    transaction.on_commit(_do)


def delete_group_clones(*, instance, model, lookup_factory):
    def _do():
        assignments = model.objects.filter(zabbixconfigurationgroup_id=instance.assigned_object_id).select_related('assigned_object_type')

        for assigned in assignments:
            lookup = lookup_factory(instance, assigned)
            model.objects.filter(**lookup).delete()

    transaction.on_commit(_do)
