import copy as _copy

from collections import OrderedDict

from django.db.models import Model, QuerySet
from django.db.models.manager import BaseManager
from django.contrib.contenttypes.models import ContentType

from nbxsync.constants import PATH_LABELS
from nbxsync.models import ZabbixServerAssignment, ZabbixHostgroupAssignment, ZabbixHostInterface, ZabbixHostInventory, ZabbixMacroAssignment, ZabbixTagAssignment, ZabbixTemplateAssignment, ZabbixConfigurationGroupAssignment
from nbxsync.settings import get_plugin_settings
from nbxsync.tables import ZabbixHostgroupAssignmentObjectViewTable, ZabbixMacroAssignmentObjectViewTable, ZabbixServerAssignmentObjectViewTable, ZabbixTagAssignmentObjectViewTable, ZabbixTemplateAssignmentObjectViewTable


def get_zabbixassignments_for_request(instance, request):
    """
    Return Zabbix context for views/templates, including rendered tables.
    Requires `request` to be passed in for table configuration.
    """
    assignments = get_assigned_zabbixobjects(instance)
    content_type = ContentType.objects.get_for_model(instance)

    def table_or_none(data, table_cls, attach_instance=False):
        if data:
            table = table_cls(data)
            table.configure(request)
            if attach_instance:
                table.instance = instance
            return table
        return None

    return {
        'zabbixserver_assignments_table': table_or_none(assignments.get('server_assignments'), ZabbixServerAssignmentObjectViewTable),
        'zabbix_template_table': table_or_none(assignments['templates'], ZabbixTemplateAssignmentObjectViewTable),
        'zabbix_macro_table': table_or_none(assignments['macros'], ZabbixMacroAssignmentObjectViewTable, attach_instance=True),
        'zabbix_tag_table': table_or_none(assignments['tags'], ZabbixTagAssignmentObjectViewTable),
        'zabbix_hostgroup_table': table_or_none(assignments['hostgroups'], ZabbixHostgroupAssignmentObjectViewTable),
        'hostinventory_assignment': assignments.get('hostinventory'),
        'configurationgroup_assignment': assignments.get('configurationgroup'),
        'object': instance,
        'content_type': content_type,
    }


def get_assigned_zabbixobjects(instance, zabbixserver=None):
    """
    Return raw Zabbix assignment lists (direct + inherited) without any table formatting.

    When *zabbixserver* is given, server-scoped objects (templates, hostgroups,
    host interfaces) are filtered to that server only.  Macros, tags, inventory
    and configuration-group assignments are server-agnostic and returned
    unfiltered.
    """
    content_type = ContentType.objects.get_for_model(instance)

    # Direct assignments — server-scoped querysets are filtered conditionally
    templates_qs = ZabbixTemplateAssignment.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id).select_related('zabbixtemplate')
    if zabbixserver:
        templates_qs = templates_qs.filter(zabbixtemplate__zabbixserver=zabbixserver)
    direct_templates = list(templates_qs)

    direct_macros = list(ZabbixMacroAssignment.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id).select_related('zabbixmacro'))
    direct_tags = list(ZabbixTagAssignment.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id).select_related('zabbixtag'))

    hostgroups_qs = ZabbixHostgroupAssignment.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id).select_related('zabbixhostgroup')
    if zabbixserver:
        hostgroups_qs = hostgroups_qs.filter(zabbixhostgroup__zabbixserver=zabbixserver)
    direct_hostgroups = list(hostgroups_qs)

    hostinterfaces_qs = ZabbixHostInterface.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id)
    if zabbixserver:
        hostinterfaces_qs = hostinterfaces_qs.filter(zabbixserver=zabbixserver)
    direct_hostinterfaces = list(hostinterfaces_qs)

    direct_server_assignments = list(ZabbixServerAssignment.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id).select_related('zabbixproxy', 'zabbixproxygroup'))

    hostinventory = ZabbixHostInventory.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id).first()
    direct_configurationgroup = ZabbixConfigurationGroupAssignment.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id).first()

    inherited = resolve_inherited_zabbix_assignments(instance, zabbixserver)

    if not hostinventory:
        hostinventory = inherited.get('hostinventory')

    configurationgroup = direct_configurationgroup or next(iter(inherited.get('configurationgroups', {}).values()), None)

    def merge(direct, inherited_map, key):
        direct_ids = {getattr(obj, key) for obj in direct}
        inherited_filtered = [obj for obj in inherited_map.values() if getattr(obj, key) not in direct_ids]
        return direct + inherited_filtered

    # Merge direct + inherited (direct takes priority)
    # ZabbixHostInterfaces assigned to SiteGroup/Role/Site are resolved
    # naturally by the inheritance chain. If the interface lacks an IP,
    # HostInterfaceSync.get_create_params() falls back to the device's
    # primary IP automatically.
    hostinterfaces = merge(direct_hostinterfaces, inherited.get('hostinterfaces', {}), 'id')

    # Merge direct + inherited (direct takes priority)
    merged_templates = merge(direct_templates, inherited['templates'], 'zabbixtemplate_id')
    merged_hostgroups = merge(direct_hostgroups, inherited['hostgroups'], 'zabbixhostgroup_id')
    merged_tags = merge(direct_tags, inherited['tags'], 'id')

    return {
        'templates': merged_templates,
        'macros': merge(direct_macros, inherited['macros'], 'zabbixmacro_id'),
        'tags': merged_tags,
        'hostgroups': merged_hostgroups,
        'hostinterfaces': hostinterfaces,
        'hostinventory': hostinventory,
        'configurationgroup': configurationgroup,
        'server_assignments': merge(direct_server_assignments, inherited.get('server_assignments', {}), 'zabbixserver_id'),
    }


def resolve_inherited_zabbix_assignments(assigned_object, zabbixserver=None):
    resolved_templates = OrderedDict()
    resolved_server_assignments = OrderedDict()
    resolved_hostinterfaces = OrderedDict()
    resolved_hostinventory = None
    resolved_macros = OrderedDict()
    resolved_tags = OrderedDict()
    resolved_hostgroups = OrderedDict()
    resolved_configurationgroups = OrderedDict()
    seen_template_ids = set()
    seen_macro_ids = set()
    seen_tag_ids = set()
    seen_hostgroup_ids = set()
    seen_configurationgroup_ids = set()

    def resolve_path(obj, path):
        cur = obj
        for attr in path:
            cur = getattr(cur, attr, None)
            if cur is None:
                return None
            # If the attribute is a manager or queryset, take the first related object
            if isinstance(cur, (BaseManager, QuerySet)):
                cur = cur.first()
            # If it's something that still isn't a model instance after collapsing, bail
            if cur is None:
                return None
        return cur

    pluginsettings = get_plugin_settings()
    for path in pluginsettings.inheritance_chain:
        related_obj = resolve_path(assigned_object, path)
        # label = '.'.join(path)

        if not related_obj:
            # print(f'Path {label} not found or is None.')
            continue

        ct = ContentType.objects.get_for_model(related_obj)
        templates = ZabbixTemplateAssignment.objects.filter(assigned_object_type=ct, assigned_object_id=related_obj.pk).select_related('zabbixtemplate')
        macros = ZabbixMacroAssignment.objects.filter(assigned_object_type=ct, assigned_object_id=related_obj.pk).select_related('zabbixmacro')
        tags = ZabbixTagAssignment.objects.filter(assigned_object_type=ct, assigned_object_id=related_obj.pk).select_related('zabbixtag')
        hostgroups = ZabbixHostgroupAssignment.objects.filter(assigned_object_type=ct, assigned_object_id=related_obj.pk).select_related('zabbixhostgroup')
        configurationgroups = ZabbixConfigurationGroupAssignment.objects.filter(assigned_object_type=ct, assigned_object_id=related_obj.pk).select_related('zabbixconfigurationgroup')

        if zabbixserver:
            templates = templates.filter(zabbixtemplate__zabbixserver=zabbixserver)
            hostgroups = hostgroups.filter(zabbixhostgroup__zabbixserver=zabbixserver)

        server_assignments = ZabbixServerAssignment.objects.filter(assigned_object_type=ct, assigned_object_id=related_obj.pk).select_related('zabbixproxy', 'zabbixproxygroup')
        hostinterfaces = ZabbixHostInterface.objects.filter(assigned_object_type=ct, assigned_object_id=related_obj.pk)
        hostinventory = ZabbixHostInventory.objects.filter(assigned_object_type=ct, assigned_object_id=related_obj.pk).first()
        # print(f'[Resolved from {label}] {related_obj}: inherited {len(templates)} templates, {len(macros)} macros, {len(tags)} tags, {len(hostgroups)} hostgroups, {len(configurationgroups)} configurationgroups,')

        for template in templates:
            if template.zabbixtemplate_id not in seen_template_ids:
                template._inherited_from = PATH_LABELS.get(path, '.'.join(path))
                resolved_templates[template.zabbixtemplate_id] = template
                seen_template_ids.add(template.zabbixtemplate_id)
        for sa in server_assignments:
            if sa.zabbixserver_id not in resolved_server_assignments:
                sa._inherited_from = PATH_LABELS.get(path, '.'.join(path))
                resolved_server_assignments[sa.zabbixserver_id] = sa

        if hostinventory and not resolved_hostinventory:
            hostinventory._inherited_from = PATH_LABELS.get(path, '.'.join(path))
            resolved_hostinventory = hostinventory

        for hi in hostinterfaces:
            if hi.id not in resolved_hostinterfaces:
                hi._inherited_from = PATH_LABELS.get(path, '.'.join(path))
                resolved_hostinterfaces[hi.id] = hi

        for macro in macros:
            if macro.zabbixmacro_id not in seen_macro_ids:
                macro._inherited_from = PATH_LABELS.get(path, '.'.join(path))
                resolved_macros[macro.zabbixmacro_id] = macro
                seen_macro_ids.add(macro.zabbixmacro_id)

        for tag in tags:
            if tag.id not in seen_tag_ids:
                tag._inherited_from = PATH_LABELS.get(path, '.'.join(path))
                resolved_tags[tag.id] = tag
                seen_tag_ids.add(tag.id)

        for hostgroup in hostgroups:
            if hostgroup.zabbixhostgroup_id not in seen_hostgroup_ids:
                hostgroup._inherited_from = PATH_LABELS.get(path, '.'.join(path))
                resolved_hostgroups[hostgroup.zabbixhostgroup_id] = hostgroup
                seen_hostgroup_ids.add(hostgroup.zabbixhostgroup_id)

        for configurationgroup in configurationgroups:
            if configurationgroup.zabbixconfigurationgroup_id not in seen_configurationgroup_ids:
                configurationgroup._inherited_from = PATH_LABELS.get(path, '.'.join(path))
                resolved_configurationgroups[configurationgroup.zabbixconfigurationgroup_id] = configurationgroup
                seen_configurationgroup_ids.add(configurationgroup.zabbixconfigurationgroup_id)

    return {
        'server_assignments': resolved_server_assignments,
        'hostinterfaces': resolved_hostinterfaces,
        'hostinventory': resolved_hostinventory,
        'templates': resolved_templates,
        'macros': resolved_macros,
        'tags': resolved_tags,
        'hostgroups': resolved_hostgroups,
        'configurationgroups': resolved_configurationgroups,
    }
