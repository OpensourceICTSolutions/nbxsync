from django.db import transaction

from nbxsync.models import ZabbixServerAssignment, ZabbixTemplateAssignment, ZabbixTagAssignment, ZabbixHostgroupAssignment, ZabbixMacroAssignment, ZabbixHostInterface
from nbxsync.utils.cfggroup.helpers import get_configgroup_ct_id, propagate_group_assignment, build_defaults_from_instance, iter_configgroup_members

COMMON_EXCLUDE = {
    'id',
    'pk',
    'assigned_object_id',
    'assigned_object_type',
    'assigned_object',
    'created',
    'last_updated',
    'custom_field_data',
}

DEFAULT_EXCLUDE_ASSIGNMENTS = COMMON_EXCLUDE | {
    'last_sync',
    'last_sync_state',
    'last_sync_message',
}

DEFAULT_EXCLUDE_SERVER = DEFAULT_EXCLUDE_ASSIGNMENTS
DEFAULT_EXCLUDE_TEMPLATE = DEFAULT_EXCLUDE_ASSIGNMENTS
DEFAULT_EXCLUDE_TAG = DEFAULT_EXCLUDE_ASSIGNMENTS
DEFAULT_EXCLUDE_HOSTGROUP = DEFAULT_EXCLUDE_ASSIGNMENTS
DEFAULT_EXCLUDE_MACRO_CREATE = COMMON_EXCLUDE
DEFAULT_EXCLUDE_HOSTINTERFACE = COMMON_EXCLUDE | {
    'interfaceid',
    'last_sync',
    'last_sync_state',
    'last_sync_message',
    'parent',
    'zabbixconfigurationgroup',
    'ip',
}


def resync_zabbixconfigurationgroupassignment(instance):
    configgroup = instance.zabbixconfigurationgroup
    if configgroup is None:
        return

    configgroup_ct_id = get_configgroup_ct_id()

    # Server assignments
    server_parents = ZabbixServerAssignment.objects.filter(assigned_object_type_id=configgroup_ct_id, assigned_object_id=configgroup.id)
    for parent in server_parents:

        def server_lookup_factory(inst, assigned):
            return {
                'zabbixserver': inst.zabbixserver,
                'assigned_object_type': assigned.assigned_object_type,
                'assigned_object_id': assigned.assigned_object_id,
            }

        propagate_group_assignment(instance=parent, model=ZabbixServerAssignment, lookup_factory=server_lookup_factory, default_exclude=DEFAULT_EXCLUDE_SERVER)

    # Template assignments
    template_parents = ZabbixTemplateAssignment.objects.filter(assigned_object_type_id=configgroup_ct_id, assigned_object_id=configgroup.id)
    for parent in template_parents:

        def template_lookup_factory(inst, assigned):
            return {
                'zabbixtemplate': inst.zabbixtemplate,
                'assigned_object_type': assigned.assigned_object_type,
                'assigned_object_id': assigned.assigned_object_id,
            }

        propagate_group_assignment(instance=parent, model=ZabbixTemplateAssignment, lookup_factory=template_lookup_factory, default_exclude=DEFAULT_EXCLUDE_TEMPLATE)

    # Tag assignments
    tag_parents = ZabbixTagAssignment.objects.filter(assigned_object_type_id=configgroup_ct_id, assigned_object_id=configgroup.id)
    for parent in tag_parents:

        def tag_lookup_factory(inst, assigned):
            return {
                'zabbixtag': inst.zabbixtag,
                'assigned_object_type': assigned.assigned_object_type,
                'assigned_object_id': assigned.assigned_object_id,
            }

        propagate_group_assignment(instance=parent, model=ZabbixTagAssignment, lookup_factory=tag_lookup_factory, default_exclude=DEFAULT_EXCLUDE_TAG)

    # HostGroup assignments
    hostgroup_parents = ZabbixHostgroupAssignment.objects.filter(assigned_object_type_id=configgroup_ct_id, assigned_object_id=configgroup.id)
    for parent in hostgroup_parents:

        def hostgroup_lookup_factory(inst, assigned):
            return {'zabbixhostgroup': inst.zabbixhostgroup, 'assigned_object_type': assigned.assigned_object_type, 'assigned_object_id': assigned.assigned_object_id}

        propagate_group_assignment(instance=parent, model=ZabbixHostgroupAssignment, lookup_factory=hostgroup_lookup_factory, default_exclude=DEFAULT_EXCLUDE_HOSTGROUP)

    # Macro assignments
    macro_parents = ZabbixMacroAssignment.objects.filter(assigned_object_type_id=configgroup_ct_id, assigned_object_id=configgroup.id)
    for parent in macro_parents:

        def macro_lookup_factory(inst, assigned):
            return {'zabbixmacro': inst.zabbixmacro, 'is_regex': inst.is_regex, 'context': inst.context, 'value': inst.value, 'assigned_object_type': assigned.assigned_object_type, 'assigned_object_id': assigned.assigned_object_id}

        propagate_group_assignment(instance=parent, model=ZabbixMacroAssignment, lookup_factory=macro_lookup_factory, default_exclude=DEFAULT_EXCLUDE_MACRO_CREATE, defaults_extra={'parent': parent})

    # Host interfaces
    def _sync_hostinterfaces():
        hostinterface_parents = ZabbixHostInterface.objects.filter(assigned_object_type_id=configgroup_ct_id, assigned_object_id=configgroup.id).select_related('assigned_object_type')

        for parent in hostinterface_parents:
            for assigned in iter_configgroup_members(parent):
                primary_ip = getattr(assigned.assigned_object, 'primary_ip', None)
                if not primary_ip:
                    continue

                lookup = {
                    'zabbixserver': parent.zabbixserver,
                    'interface_type': parent.interface_type,
                    'type': parent.type,
                    'assigned_object_type': assigned.assigned_object_type,
                    'assigned_object_id': assigned.assigned_object_id,
                }

                defaults = build_defaults_from_instance(
                    parent,
                    exclude=DEFAULT_EXCLUDE_HOSTINTERFACE,
                    extra={'ip': primary_ip, 'dns': primary_ip.dns_name, 'useip': parent.useip, 'zabbixconfigurationgroup': configgroup, 'parent': parent},
                )

                ZabbixHostInterface.objects.update_or_create(**lookup, defaults=defaults)

    transaction.on_commit(_sync_hostinterfaces)
