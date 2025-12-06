from collections import OrderedDict

from django.db.models import Model, QuerySet
from django.db.models.manager import BaseManager
from django.contrib.contenttypes.models import ContentType

from nbxsync.constants import PATH_LABELS
from nbxsync.models import ZabbixHostgroupAssignment, ZabbixHostInterface, ZabbixHostInventory, ZabbixMacroAssignment, ZabbixTagAssignment, ZabbixTemplateAssignment, ZabbixConfigurationGroupAssignment
from nbxsync.settings import get_plugin_settings
from nbxsync.tables import ZabbixHostgroupAssignmentObjectViewTable, ZabbixMacroAssignmentObjectViewTable, ZabbixTagAssignmentObjectViewTable, ZabbixTemplateAssignmentObjectViewTable


def get_zabbixassignments_for_request(instance, request):
    """
    Return Zabbix context for views/templates, including rendered tables.
    Requires `request` to be passed in for table configuration.
    """
    assignments = get_assigned_zabbixobjects(instance)
    content_type = ContentType.objects.get_for_model(instance)

    def table_or_none(data, table_cls):
        if data:
            table = table_cls(data)
            table.configure(request)
            return table
        return None

    return {
        'zabbix_template_table': table_or_none(assignments['templates'], ZabbixTemplateAssignmentObjectViewTable),
        'zabbix_macro_table': table_or_none(assignments['macros'], ZabbixMacroAssignmentObjectViewTable),
        'zabbix_tag_table': table_or_none(assignments['tags'], ZabbixTagAssignmentObjectViewTable),
        'zabbix_hostgroup_table': table_or_none(assignments['hostgroups'], ZabbixHostgroupAssignmentObjectViewTable),
        'object': instance,
        'content_type': content_type,
    }


def get_assigned_zabbixobjects(instance):
    """
    Return raw Zabbix assignment lists (direct + inherited) without any table formatting.
    """
    content_type = ContentType.objects.get_for_model(instance)

    # Direct assignments
    direct_templates = list(ZabbixTemplateAssignment.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id).select_related('zabbixtemplate'))
    direct_macros = list(ZabbixMacroAssignment.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id).select_related('zabbixmacro'))
    direct_tags = list(ZabbixTagAssignment.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id).select_related('zabbixtag'))
    direct_hostgroups = list(ZabbixHostgroupAssignment.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id).select_related('zabbixhostgroup'))
    hostinterfaces = list(ZabbixHostInterface.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id))
    hostinventory = ZabbixHostInventory.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id).first()
    configurationgroup = ZabbixConfigurationGroupAssignment.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id).first()

    inherited = resolve_inherited_zabbix_assignments(instance)

    def merge(direct, inherited_map, key):
        direct_ids = {getattr(obj, key) for obj in direct}
        inherited_filtered = [obj for obj in inherited_map.values() if getattr(obj, key) not in direct_ids]
        return direct + inherited_filtered

    return {
        'templates': merge(direct_templates, inherited['templates'], 'zabbixtemplate_id'),
        'macros': merge(direct_macros, inherited['macros'], 'zabbixmacro_id'),
        'tags': merge(direct_tags, inherited['tags'], 'id'),
        'hostgroups': merge(direct_hostgroups, inherited['hostgroups'], 'zabbixhostgroup_id'),
        'hostinterfaces': hostinterfaces,
        'hostinventory': hostinventory,
        'configurationgroup': configurationgroup,
    }


def resolve_inherited_zabbix_assignments(assigned_object):
    resolved_templates = OrderedDict()
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
            # If it’s something that still isn’t a model instance after collapsing, bail
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

        # print(f'[Resolved from {label}] {related_obj}: inherited {len(templates)} templates, {len(macros)} macros, {len(tags)} tags, {len(hostgroups)} hostgroups, {len(configurationgroups)} configurationgroups,')

        for template in templates:
            if template.zabbixtemplate_id not in seen_template_ids:
                template._inherited_from = PATH_LABELS.get(path, '.'.join(path))
                resolved_templates[template.zabbixtemplate_id] = template
                seen_template_ids.add(template.zabbixtemplate_id)

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
        'templates': resolved_templates,
        'macros': resolved_macros,
        'tags': resolved_tags,
        'hostgroups': resolved_hostgroups,
        'configurationgroups': resolved_configurationgroups,
    }
