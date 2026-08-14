import copy as _copy
from collections import OrderedDict

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, QuerySet
from django.db.models.manager import BaseManager

from dcim.models import DeviceRole, Region, SiteGroup
from extras.models import Tag
from virtualization.models import VirtualMachine

from nbxsync.constants import PATH_LABELS
from nbxsync.models import ZabbixConfigurationGroupAssignment, ZabbixHostgroupAssignment, ZabbixHostInterface, ZabbixHostInventory, ZabbixMacroAssignment, ZabbixServerAssignment, ZabbixTagAssignment, ZabbixTemplateAssignment, ZabbixTemplateRule
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


def _merge_direct_and_inherited(direct_list, inherited_map, key):
    """Direct assignments win; inherited rows with the same key are skipped."""
    inherited_map = inherited_map or {}
    direct_ids = {getattr(obj, key) for obj in direct_list}
    inherited_filtered = [obj for obj in inherited_map.values() if getattr(obj, key) not in direct_ids]
    return list(direct_list) + inherited_filtered


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

    direct_server_assignments = ZabbixServerAssignment.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id).select_related('zabbixproxy', 'zabbixproxygroup')
    if zabbixserver:
        direct_server_assignments = direct_server_assignments.filter(zabbixserver=zabbixserver)
    direct_server_assignments = list(direct_server_assignments)

    hostinventory = ZabbixHostInventory.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id).first()
    direct_configurationgroup = ZabbixConfigurationGroupAssignment.objects.filter(assigned_object_type=content_type, assigned_object_id=instance.id).first()

    inherited = resolve_inherited_zabbix_assignments(instance, zabbixserver)

    if not hostinventory:
        hostinventory = inherited.get('hostinventory')

    configurationgroup = direct_configurationgroup or next(iter(inherited.get('configurationgroups', {}).values()), None)

    # Merge direct + inherited (direct takes priority)
    # ZabbixHostInterfaces assigned to SiteGroup/Role/Site are resolved
    # naturally by the inheritance chain. If the interface lacks an IP,
    # HostInterfaceSync.get_create_params() falls back to the device's
    # primary IP automatically.
    hostinterfaces = _merge_direct_and_inherited(direct_hostinterfaces, inherited.get('hostinterfaces', {}), 'id')
    # Expand ConfigGroup-defined interfaces for this specific instance.
    # When a ConfigGroup is assigned at Site/Platform level, the signal-based
    # propagation cannot clone per-device interfaces (Site has no primary_ip).
    # Resolve them here so HostSync and HostInterfaceSync get device-specific interfaces.
    if configurationgroup:
        cg_ct = ContentType.objects.get_for_model(configurationgroup.zabbixconfigurationgroup)
        cg_interfaces = ZabbixHostInterface.objects.filter(
            assigned_object_type=cg_ct,
            assigned_object_id=configurationgroup.zabbixconfigurationgroup_id,
        )
        existing_types = {hi.type for hi in hostinterfaces}
        primary_ip = getattr(instance, 'primary_ip4', None) or getattr(instance, 'primary_ip6', None)
        for cg_iface in cg_interfaces:
            if cg_iface.type not in existing_types:
                # Clone the interface with the device's primary IP
                child = _copy.copy(cg_iface)
                child.pk = None
                child._is_inherited_copy = True
                child.assigned_object_type = content_type
                child.assigned_object_id = instance.id
                child.ip = primary_ip if primary_ip else None
                hostinterfaces.append(child)

    # Merge direct + inherited (direct takes priority).
    # TemplateRule matching runs after this so explicit assignments always win.
    merged_templates = _merge_direct_and_inherited(direct_templates, inherited['templates'], 'zabbixtemplate_id')
    resolved_template_ids = {getattr(obj, 'zabbixtemplate_id') for obj in merged_templates}
    merged_hostgroups = _merge_direct_and_inherited(direct_hostgroups, inherited['hostgroups'], 'zabbixhostgroup_id')
    resolved_hostgroup_ids = {getattr(obj, 'zabbixhostgroup_id') for obj in merged_hostgroups}
    merged_tags = _merge_direct_and_inherited(direct_tags, inherited['tags'], 'id')
    resolved_tag_ids = {obj.zabbixtag_id for obj in merged_tags}

    # ConfigGroup members are also expanded at resolve time so host sync does
    # not depend on the async RQ propagate job having already cloned rows onto
    # the device/site. Durable propagation remains for UI; this path is the
    # sync-time source of truth.
    if configurationgroup:
        cg = configurationgroup.zabbixconfigurationgroup
        cg_ct = ContentType.objects.get_for_model(cg)
        cg_templates = ZabbixTemplateAssignment.objects.filter(
            assigned_object_type=cg_ct,
            assigned_object_id=cg.id,
        ).select_related('zabbixtemplate')
        if zabbixserver is not None:
            cg_templates = cg_templates.filter(zabbixtemplate__zabbixserver=zabbixserver)
        for ta in cg_templates:
            if ta.zabbixtemplate_id in resolved_template_ids:
                continue
            wrapper = _copy.copy(ta)
            wrapper.pk = None
            wrapper._is_inherited_copy = True
            wrapper.assigned_object_type = content_type
            wrapper.assigned_object_id = instance.id
            merged_templates.append(wrapper)
            resolved_template_ids.add(ta.zabbixtemplate_id)

    platform = getattr(instance, 'platform', None)
    role = getattr(instance, 'role', None)
    device_type = getattr(instance, 'device_type', None)
    manufacturer_id = getattr(device_type, 'manufacturer_id', None) if device_type is not None else None
    try:
        object_tag_slugs = {tag.slug for tag in instance.tags.all()} if hasattr(instance, 'tags') else set()
    except Exception:
        object_tag_slugs = set()
    rules_qs = ZabbixTemplateRule.objects.filter(enabled=True).select_related('zabbixtemplate', 'zabbixhostgroup', 'zabbixtag', 'manufacturer')
    if zabbixserver:
        rules_qs = rules_qs.filter(zabbixtemplate__zabbixserver=zabbixserver)
    for rule in rules_qs.order_by('priority', 'name'):
        if not rule.matches(
            platform.name if platform else None,
            role_name=role.name if role else None,
            netbox_tags=object_tag_slugs,
            manufacturer_id=manufacturer_id,
        ):
            continue
        inherited_from = f'Regex: {rule.name}'
        if rule.zabbixtemplate_id and rule.zabbixtemplate_id not in resolved_template_ids:
            wrapper = ZabbixTemplateAssignment(
                zabbixtemplate=rule.zabbixtemplate,
                assigned_object_type=content_type,
                assigned_object_id=instance.id,
            )
            wrapper.pk = None
            wrapper._is_inherited_copy = True
            wrapper._inherited_from = inherited_from
            merged_templates.append(wrapper)
            resolved_template_ids.add(rule.zabbixtemplate_id)
        if rule.zabbixhostgroup_id and rule.zabbixhostgroup_id not in resolved_hostgroup_ids:
            wrapper = ZabbixHostgroupAssignment(
                zabbixhostgroup=rule.zabbixhostgroup,
                assigned_object_type=content_type,
                assigned_object_id=instance.id,
            )
            wrapper.pk = None
            wrapper._is_inherited_copy = True
            wrapper._inherited_from = inherited_from
            merged_hostgroups.append(wrapper)
            resolved_hostgroup_ids.add(rule.zabbixhostgroup_id)
        if rule.zabbixtag_id and rule.zabbixtag_id not in resolved_tag_ids:
            wrapper = ZabbixTagAssignment(
                zabbixtag=rule.zabbixtag,
                assigned_object_type=content_type,
                assigned_object_id=instance.id,
            )
            wrapper.pk = None
            wrapper._is_inherited_copy = True
            wrapper._inherited_from = inherited_from
            merged_tags.append(wrapper)
            resolved_tag_ids.add(rule.zabbixtag_id)

    return {
        'templates': merged_templates,
        'macros': _merge_direct_and_inherited(direct_macros, inherited['macros'], 'zabbixmacro_id'),
        'tags': merged_tags,
        'hostgroups': merged_hostgroups,
        'hostinterfaces': hostinterfaces,
        'hostinventory': hostinventory,
        'configurationgroup': configurationgroup,
        'server_assignments': _merge_direct_and_inherited(direct_server_assignments, inherited.get('server_assignments', {}), 'zabbixserver_id'),
    }


def _walk_ancestors(obj, parent_attr='parent'):
    """Yield obj, then each ancestor via parent_attr, until None.

    Includes obj itself so callers can check assignments on the
    starting object AND all ancestors. Cycle-safe via a seen-set.
    """
    if obj is None:
        return
    seen = set()
    cur = obj
    while cur is not None and cur not in seen:
        yield cur
        seen.add(cur)
        cur = getattr(cur, parent_attr, None)


def _inheritance_source(path, source_obj):
    label = PATH_LABELS.get(path, '.'.join(path))
    if isinstance(source_obj, (SiteGroup, Region, DeviceRole)):
        return f'{label}: {source_obj}'
    return label


def resolve_inherited_zabbix_assignments(assigned_object, zabbixserver=None):  # noqa: C901
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
        seen = set()
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
            if cur in seen:
                return None  # cycle detected
            seen.add(cur)
        return cur

    pluginsettings = get_plugin_settings()

    # --- Collect phase ---
    # Walk every inheritance-chain path and gather (content_type, object_pk, label)
    # triples in leaf-first order. No queries are issued here. The seen_objects
    # dedup preserves the original "first path an object is seen on wins" semantics.
    triples = []
    seen_objects = set()

    # Tag-targeted assignments resolve at object level: an object inherits every
    # assignment pointed at a NetBox Tag it carries. Collected before the
    # hierarchy chain so an attribute-level source beats a distant hierarchy
    # source on first-seen dedup. Guarded: only taggable models enter, and the
    # tagging manager is never allowed to abort resolution.
    if hasattr(assigned_object, 'tags'):
        tag_ct = ContentType.objects.get_for_model(Tag, for_concrete_model=False)
        try:
            object_tags = list(assigned_object.tags.all())
        except Exception:
            object_tags = []
        for tag in object_tags:
            object_key = (tag_ct.pk, tag.pk)
            if object_key in seen_objects:
                continue
            seen_objects.add(object_key)
            triples.append((tag_ct, tag.pk, f'Tag: {tag.name}'))

    for path in pluginsettings.inheritance_chain:
        # 'device'-prefixed paths describe the *associated physical device*
        # (the VDC's parent, or — since NetBox 4.3 — a VM's hosting device).
        # For a VirtualMachine that association is the hypervisor/sidecar, so
        # walking these paths would leak host properties (manufacturer, role,
        # hardware templates) onto the guest. VDCs keep the paths: a VDC is
        # part of its parent device by definition.
        if path and path[0] == 'device' and isinstance(assigned_object, VirtualMachine):
            continue

        related_obj = resolve_path(assigned_object, path)

        if not related_obj:
            continue

        if isinstance(related_obj, (SiteGroup, Region, DeviceRole)):
            objects_to_check = _walk_ancestors(related_obj)
        else:
            objects_to_check = (related_obj,)

        for ancestor_obj in objects_to_check:
            ct = ContentType.objects.get_for_model(ancestor_obj)
            object_key = (ct.pk, ancestor_obj.pk)
            if object_key in seen_objects:
                continue
            seen_objects.add(object_key)
            label = _inheritance_source(path, ancestor_obj)
            triples.append((ct, ancestor_obj.pk, label))

    resolved_hostinventory = _resolve_inherited_assignments_batched(
        triples,
        zabbixserver,
        resolved_templates,
        resolved_server_assignments,
        resolved_hostinterfaces,
        resolved_macros,
        resolved_tags,
        resolved_hostgroups,
        resolved_configurationgroups,
        seen_template_ids,
        seen_macro_ids,
        seen_tag_ids,
        seen_hostgroup_ids,
        seen_configurationgroup_ids,
    )

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


def _resolve_inherited_assignments_batched(
    triples,
    zabbixserver,
    resolved_templates,
    resolved_server_assignments,
    resolved_hostinterfaces,
    resolved_macros,
    resolved_tags,
    resolved_hostgroups,
    resolved_configurationgroups,
    seen_template_ids,
    seen_macro_ids,
    seen_tag_ids,
    seen_hostgroup_ids,
    seen_configurationgroup_ids,
):
    """Batch-query all assignment models across every collected ancestor triple.

    Replaces the former per-ancestor 7-query loop: one query per assignment model
    (plus one for hostinventory) instead of 7×N. Distribution iterates the batched
    rows in ancestor (triple) order so first-seen-wins dedup matches the original
    per-ancestor loop exactly.
    """
    if not triples:
        return None

    # Build a single Q OR across all (content_type, object_pk) pairs per model.
    base_q = Q()
    for ct, pk, _label in triples:
        base_q |= Q(assigned_object_type=ct, assigned_object_id=pk)
    label_by_obj = {(ct.pk, pk): label for ct, pk, label in triples}

    def _batch(model, *, select_related=(), server_filter=None):
        qs = model.objects.filter(base_q)
        if select_related:
            qs = qs.select_related(*select_related)
        if zabbixserver and server_filter:
            qs = qs.filter(**server_filter)
        return qs

    templates_qs = _batch(
        ZabbixTemplateAssignment,
        select_related=('zabbixtemplate',),
        server_filter={'zabbixtemplate__zabbixserver': zabbixserver},
    )
    macros_qs = _batch(ZabbixMacroAssignment, select_related=('zabbixmacro',))
    tags_qs = _batch(ZabbixTagAssignment, select_related=('zabbixtag',))
    hostgroups_qs = _batch(
        ZabbixHostgroupAssignment,
        select_related=('zabbixhostgroup',),
        server_filter={'zabbixhostgroup__zabbixserver': zabbixserver},
    )
    configurationgroups_qs = _batch(ZabbixConfigurationGroupAssignment, select_related=('zabbixconfigurationgroup',))
    server_assignments_qs = _batch(
        ZabbixServerAssignment,
        select_related=('zabbixproxy', 'zabbixproxygroup'),
        server_filter={'zabbixserver': zabbixserver},
    )
    hostinterfaces_qs = _batch(ZabbixHostInterface, server_filter={'zabbixserver': zabbixserver})

    # Group rows by their (assigned_object_type_id, assigned_object_id) source so
    # distribution can walk ancestors in collection (leaf-first) order.
    def _group(qs):
        grouped = {}
        for obj in qs:
            key = (obj.assigned_object_type_id, obj.assigned_object_id)
            grouped.setdefault(key, []).append(obj)
        return grouped

    templates_by_obj = _group(templates_qs)
    macros_by_obj = _group(macros_qs)
    tags_by_obj = _group(tags_qs)
    hostgroups_by_obj = _group(hostgroups_qs)
    configurationgroups_by_obj = _group(configurationgroups_qs)
    server_assignments_by_obj = _group(server_assignments_qs)
    hostinterfaces_by_obj = _group(hostinterfaces_qs)

    resolved_hostinventory = None
    hostinventory_by_obj = _group(ZabbixHostInventory.objects.filter(base_q))

    for ct, pk, label in triples:
        key = (ct.pk, pk)
        inherited_from = label_by_obj[key]

        for template in templates_by_obj.get(key, []):
            if template.zabbixtemplate_id not in seen_template_ids:
                template._inherited_from = inherited_from
                resolved_templates[template.zabbixtemplate_id] = template
                seen_template_ids.add(template.zabbixtemplate_id)
        for sa in server_assignments_by_obj.get(key, []):
            if sa.zabbixserver_id not in resolved_server_assignments:
                sa._inherited_from = inherited_from
                resolved_server_assignments[sa.zabbixserver_id] = sa
        for hi in hostinterfaces_by_obj.get(key, []):
            if hi.id not in resolved_hostinterfaces:
                hi._inherited_from = inherited_from
                resolved_hostinterfaces[hi.id] = hi
        for macro in macros_by_obj.get(key, []):
            if macro.zabbixmacro_id not in seen_macro_ids:
                macro._inherited_from = inherited_from
                resolved_macros[macro.zabbixmacro_id] = macro
                seen_macro_ids.add(macro.zabbixmacro_id)
        for tag in tags_by_obj.get(key, []):
            if tag.id not in seen_tag_ids:
                tag._inherited_from = inherited_from
                resolved_tags[tag.id] = tag
                seen_tag_ids.add(tag.id)
        for hostgroup in hostgroups_by_obj.get(key, []):
            if hostgroup.zabbixhostgroup_id not in seen_hostgroup_ids:
                hostgroup._inherited_from = inherited_from
                resolved_hostgroups[hostgroup.zabbixhostgroup_id] = hostgroup
                seen_hostgroup_ids.add(hostgroup.zabbixhostgroup_id)
        for configurationgroup in configurationgroups_by_obj.get(key, []):
            if configurationgroup.zabbixconfigurationgroup_id not in seen_configurationgroup_ids:
                configurationgroup._inherited_from = inherited_from
                resolved_configurationgroups[configurationgroup.zabbixconfigurationgroup_id] = configurationgroup
                seen_configurationgroup_ids.add(configurationgroup.zabbixconfigurationgroup_id)

        if not resolved_hostinventory:
            inventory_rows = hostinventory_by_obj.get(key, [])
            if inventory_rows:
                hostinventory = inventory_rows[0]
                hostinventory._inherited_from = inherited_from
                resolved_hostinventory = hostinventory

    return resolved_hostinventory
