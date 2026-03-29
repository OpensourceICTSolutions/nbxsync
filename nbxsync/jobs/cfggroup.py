import logging
from django.contrib.contenttypes.models import ContentType
from django.db import transaction, models, IntegrityError

from nbxsync.models import ZabbixConfigurationGroupAssignment, ZabbixHostgroupAssignment, ZabbixHostInterface, ZabbixMacroAssignment, ZabbixServerAssignment, ZabbixTagAssignment, ZabbixTemplateAssignment
from nbxsync.utils.cfggroup.helpers import build_defaults_from_instance, is_configgroup_assignment, propagate_group_assignment
from nbxsync.utils.cfggroup.resync_zabbixconfiggroupassignment import resync_zabbixconfigurationgroupassignment

__all__ = (
    'PropagateConfigGroupAssignmentJob',
    'DeleteConfigGroupAssignmentChildrenJob',
    'PropagateServerAssignmentJob',
    'DeleteServerAssignmentClonesJob',
    'PropagateTemplateAssignmentJob',
    'DeleteTemplateAssignmentClonesJob',
    'PropagateTagAssignmentJob',
    'DeleteTagAssignmentClonesJob',
    'PropagateHostGroupAssignmentJob',
    'DeleteHostGroupAssignmentClonesJob',
    'PropagateMacroAssignmentCreateJob',
    'PropagateMacroAssignmentUpdateJob',
)

logger = logging.getLogger(__name__)

_HOSTGROUP_DEFAULT_EXCLUDE = {'id', 'pk', 'groupid', 'assigned_object_id', 'assigned_object_type', 'assigned_object', 'last_sync', 'last_sync_state', 'last_sync_message', 'created', 'last_updated', 'custom_field_data', 'zabbixconfigurationgroup'}


_MACRO_COMMON_EXCLUDE = {
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

_MACRO_EXCLUDE_CREATE = _MACRO_COMMON_EXCLUDE

_MACRO_EXCLUDE_UPDATE = _MACRO_COMMON_EXCLUDE | {
    'last_sync',
    'last_sync_state',
    'last_sync_message',
    'zabbixconfigurationgroup',
}


def _get_instance_or_warn(model, pk, job_name):
    """Return model instance by pk, or None if it no longer exists."""
    try:
        return model.objects.get(pk=pk)
    except model.DoesNotExist:
        logger.warning('%s: %s pk=%s no longer exists, skipping', job_name, model.__name__, pk)
        return None


class PropagateConfigGroupAssignmentJob:
    def __init__(self, **kwargs):
        self.assignment_pk = kwargs['assignment_pk']

    def run(self):
        instance = _get_instance_or_warn(ZabbixConfigurationGroupAssignment, self.assignment_pk, self.__class__.__name__)
        if instance is None:
            return

        if instance.zabbixconfigurationgroup is None:
            return

        logger.debug('%s: propagating pk=%s', self.__class__.__name__, self.assignment_pk)
        resync_zabbixconfigurationgroupassignment(instance)


class DeleteConfigGroupAssignmentChildrenJob:
    """
    Delete all cloned sub-assignments that were created for this
    config-group/object combination.
    """

    def __init__(self, **kwargs):
        self.configgroup_pk = kwargs['configgroup_pk']
        self.assigned_object_type_pk = kwargs['assigned_object_type_pk']
        self.assigned_object_id = kwargs['assigned_object_id']

    def run(self):
        logger.debug('%s: deleting children for configgroup_pk=%s object_type_pk=%s object_id=%s', self.__class__.__name__, self.configgroup_pk, self.assigned_object_type_pk, self.assigned_object_id)

        try:
            assigned_ct = ContentType.objects.get(pk=self.assigned_object_type_pk)
        except ContentType.DoesNotExist:
            logger.warning('%s: ContentType pk=%s not found – skipping', self.__class__.__name__, self.assigned_object_type_pk)
            return

        filter_kwargs = {'zabbixconfigurationgroup_id': self.configgroup_pk, 'assigned_object_type': assigned_ct, 'assigned_object_id': self.assigned_object_id}

        ZabbixServerAssignment.objects.filter(**filter_kwargs).delete()
        ZabbixTemplateAssignment.objects.filter(**filter_kwargs).delete()
        ZabbixTagAssignment.objects.filter(**filter_kwargs).delete()
        ZabbixHostgroupAssignment.objects.filter(**filter_kwargs).delete()
        ZabbixMacroAssignment.objects.filter(**filter_kwargs).delete()
        ZabbixHostInterface.objects.filter(**filter_kwargs).delete()


class PropagateServerAssignmentJob:
    DEFAULT_EXCLUDE = {
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

    def __init__(self, **kwargs):
        self.assignment_pk = kwargs['assignment_pk']

    def run(self):
        instance = _get_instance_or_warn(ZabbixServerAssignment, self.assignment_pk, self.__class__.__name__)
        if instance is None or not is_configgroup_assignment(instance):
            return

        def lookup_factory(inst, assigned):
            return {'zabbixserver': inst.zabbixserver, 'assigned_object_type': assigned.assigned_object_type, 'assigned_object_id': assigned.assigned_object_id}

        propagate_group_assignment(instance=instance, model=ZabbixServerAssignment, lookup_factory=lookup_factory, default_exclude=self.DEFAULT_EXCLUDE)


class DeleteServerAssignmentClonesJob:
    def __init__(self, **kwargs):
        self.configgroup_pk = kwargs['configgroup_pk']
        self.assigned_object_type_pk = kwargs['assigned_object_type_pk']
        self.zabbixserver_pk = kwargs['zabbixserver_pk']

    def run(self):
        try:
            assigned_ct = ContentType.objects.get(pk=self.assigned_object_type_pk)
        except ContentType.DoesNotExist:
            logger.warning('%s: ContentType pk=%s not found – skipping', self.__class__.__name__, self.assigned_object_type_pk)
            return

        assignments = ZabbixServerAssignment.objects.filter(zabbixconfigurationgroup_id=self.configgroup_pk).select_related('assigned_object_type')

        def _delete():
            for assigned in assignments:
                ZabbixServerAssignment.objects.filter(
                    assigned_object_type=assigned.assigned_object_type,
                    assigned_object_id=assigned.assigned_object_id,
                    zabbixconfigurationgroup_id=self.configgroup_pk,
                    zabbixserver_id=self.zabbixserver_pk,
                ).delete()

        transaction.on_commit(_delete)


class PropagateTemplateAssignmentJob:
    DEFAULT_EXCLUDE = {
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

    def __init__(self, **kwargs):
        self.assignment_pk = kwargs['assignment_pk']

    def run(self):
        instance = _get_instance_or_warn(ZabbixTemplateAssignment, self.assignment_pk, self.__class__.__name__)
        if instance is None or not is_configgroup_assignment(instance):
            return

        def lookup_factory(inst, assigned):
            return {
                'zabbixtemplate': inst.zabbixtemplate,
                'assigned_object_type': assigned.assigned_object_type,
                'assigned_object_id': assigned.assigned_object_id,
            }

        propagate_group_assignment(instance=instance, model=ZabbixTemplateAssignment, lookup_factory=lookup_factory, default_exclude=self.DEFAULT_EXCLUDE)


class DeleteTemplateAssignmentClonesJob:
    def __init__(self, **kwargs):
        self.configgroup_pk = kwargs['configgroup_pk']
        self.assigned_object_type_pk = kwargs['assigned_object_type_pk']
        self.zabbixtemplate_pk = kwargs['zabbixtemplate_pk']

    def run(self):
        assignments = ZabbixTemplateAssignment.objects.filter(zabbixconfigurationgroup_id=self.configgroup_pk).select_related('assigned_object_type')

        def _delete():
            for assigned in assignments:
                ZabbixTemplateAssignment.objects.filter(assigned_object_type=assigned.assigned_object_type, assigned_object_id=assigned.assigned_object_id, zabbixconfigurationgroup_id=self.configgroup_pk, zabbixtemplate_id=self.zabbixtemplate_pk).delete()

        transaction.on_commit(_delete)


class PropagateTagAssignmentJob:
    DEFAULT_EXCLUDE = {
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

    def __init__(self, **kwargs):
        self.assignment_pk = kwargs['assignment_pk']

    def run(self):
        instance = _get_instance_or_warn(ZabbixTagAssignment, self.assignment_pk, self.__class__.__name__)
        if instance is None or not is_configgroup_assignment(instance):
            return

        def lookup_factory(inst, assigned):
            return {'zabbixtag': inst.zabbixtag, 'assigned_object_type': assigned.assigned_object_type, 'assigned_object_id': assigned.assigned_object_id}

        propagate_group_assignment(instance=instance, model=ZabbixTagAssignment, lookup_factory=lookup_factory, default_exclude=self.DEFAULT_EXCLUDE)


class DeleteTagAssignmentClonesJob:
    def __init__(self, **kwargs):
        self.configgroup_pk = kwargs['configgroup_pk']
        self.zabbixtag_pk = kwargs['zabbixtag_pk']

    def run(self):
        assignments = ZabbixTagAssignment.objects.filter(zabbixconfigurationgroup_id=self.configgroup_pk).select_related('assigned_object_type')

        def _delete():
            for assigned in assignments:
                ZabbixTagAssignment.objects.filter(zabbixtag_id=self.zabbixtag_pk, assigned_object_type=assigned.assigned_object_type, assigned_object_id=assigned.assigned_object_id, zabbixconfigurationgroup_id=self.configgroup_pk).delete()

        transaction.on_commit(_delete)


def _build_hostgroup_defaults(instance):
    defaults = {'zabbixconfigurationgroup': instance.assigned_object}

    for field in instance._meta.concrete_fields:
        name = field.name
        if name in _HOSTGROUP_DEFAULT_EXCLUDE:
            continue

        if isinstance(field, models.ForeignKey):
            defaults[field.attname] = getattr(instance, field.attname)

    return defaults


class PropagateHostGroupAssignmentJob:
    def __init__(self, **kwargs):
        self.assignment_pk = kwargs['assignment_pk']

    def run(self):
        instance = _get_instance_or_warn(ZabbixHostgroupAssignment, self.assignment_pk, self.__class__.__name__)
        if instance is None or not is_configgroup_assignment(instance):
            return

        configurationgroup_obj = instance.assigned_object_type.get_object_for_this_type(pk=instance.assigned_object_id)

        def _propagate():
            for assigned in ZabbixConfigurationGroupAssignment.objects.filter(zabbixconfigurationgroup=configurationgroup_obj).select_related('assigned_object_type'):
                lookup = {
                    'zabbixhostgroup': instance.zabbixhostgroup,
                    'assigned_object_type': assigned.assigned_object_type,
                    'assigned_object_id': assigned.assigned_object_id,
                }

                existing = ZabbixHostgroupAssignment.objects.filter(**lookup).first()
                if existing is not None and existing.zabbixconfigurationgroup is None:
                    continue

                defaults = _build_hostgroup_defaults(instance)

                try:
                    ZabbixHostgroupAssignment.objects.update_or_create(**lookup, defaults=defaults)
                except IntegrityError:
                    ZabbixHostgroupAssignment.objects.filter(**lookup).update(**defaults)

        transaction.on_commit(_propagate)


class DeleteHostGroupAssignmentClonesJob:
    def __init__(self, **kwargs):
        self.configgroup_pk = kwargs['configgroup_pk']

    def run(self):
        assignments = ZabbixHostgroupAssignment.objects.filter(zabbixconfigurationgroup_id=self.configgroup_pk).select_related('assigned_object_type')

        def _delete():
            for assigned in assignments:
                ZabbixHostgroupAssignment.objects.filter(assigned_object_type=assigned.assigned_object_type, assigned_object_id=assigned.assigned_object_id, zabbixconfigurationgroup_id=self.configgroup_pk).delete()

        transaction.on_commit(_delete)


class PropagateMacroAssignmentCreateJob:
    def __init__(self, **kwargs):
        self.assignment_pk = kwargs['assignment_pk']

    def run(self):
        instance = _get_instance_or_warn(ZabbixMacroAssignment, self.assignment_pk, self.__class__.__name__)
        if instance is None or not is_configgroup_assignment(instance):
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

        propagate_group_assignment(instance=instance, model=ZabbixMacroAssignment, lookup_factory=lookup_factory, default_exclude=_MACRO_EXCLUDE_CREATE, defaults_extra={'parent': instance})


class PropagateMacroAssignmentUpdateJob:
    def __init__(self, **kwargs):
        self.assignment_pk = kwargs['assignment_pk']

    def run(self):
        instance = _get_instance_or_warn(ZabbixMacroAssignment, self.assignment_pk, self.__class__.__name__)
        if instance is None or not is_configgroup_assignment(instance):
            return

        updates = build_defaults_from_instance(instance, exclude=_MACRO_EXCLUDE_UPDATE)
        instance.children.exclude(zabbixconfigurationgroup__isnull=True).update(**updates)
