from collections import OrderedDict, defaultdict
from typing import Any, Callable, Iterable

from django.contrib.contenttypes.models import ContentType
from django.db.models import Model, Q, QuerySet
from django.db.models.manager import BaseManager

from nbxsync.constants import PATH_LABELS
from nbxsync.models import ZabbixConfigurationGroupAssignment, ZabbixHostInterface, ZabbixHostInventory, ZabbixHostgroupAssignment, ZabbixMacroAssignment, ZabbixTagAssignment, ZabbixTemplate, ZabbixTemplateAssignment
from nbxsync.settings import get_plugin_settings
from nbxsync.tables import ZabbixHostgroupAssignmentObjectViewTable, ZabbixMacroAssignmentObjectViewTable, ZabbixTagAssignmentObjectViewTable, ZabbixTemplateAssignmentObjectViewTable


def _template_server_filter(server):
    return Q(zabbixtemplate__zabbixserver_id=server.id)


def _hostgroup_server_filter(server):
    return Q(zabbixhostgroup__zabbixserver_id=server.id)


def _macro_server_filter(server):
    """
    Macros are attached (via generic FK) to either a ZabbixServer or a
    ZabbixTemplate. Include:
      - macros whose assigned_object IS this ZabbixServer, or
      - macros whose assigned_object is a ZabbixTemplate belonging to this
        ZabbixServer.
    """
    server_ct = ContentType.objects.get_for_model(server.__class__)
    template_ct = ContentType.objects.get_for_model(ZabbixTemplate)
    templates_on_server = ZabbixTemplate.objects.filter(zabbixserver_id=server.id).values('id')

    return Q(zabbixmacro__assigned_object_type=server_ct, zabbixmacro__assigned_object_id=server.id) | Q(zabbixmacro__assigned_object_type=template_ct, zabbixmacro__assigned_object_id__in=templates_on_server)


# Each row: (model, select_related field, dedup key attr, server-filter builder).
# server-filter builder is None for models that have no ZabbixServer relation.
_INHERITANCE_MODELS = (
    (ZabbixTemplateAssignment, 'zabbixtemplate', 'zabbixtemplate_id', _template_server_filter),
    (ZabbixMacroAssignment, 'zabbixmacro', 'zabbixmacro_id', _macro_server_filter),
    (ZabbixTagAssignment, 'zabbixtag', 'id', None),
    (ZabbixHostgroupAssignment, 'zabbixhostgroup', 'zabbixhostgroup_id', _hostgroup_server_filter),
    (ZabbixConfigurationGroupAssignment, 'zabbixconfigurationgroup', 'zabbixconfigurationgroup_id', None),
)
_RESULT_KEYS = ('templates', 'macros', 'tags', 'hostgroups', 'configurationgroups')


def get_zabbixassignments_for_request(instance, request):
    """
    Return Zabbix context for views/templates, including rendered tables.
    Requires `request` to be passed in for table configuration.
    """
    assignments = get_assigned_zabbixobjects(instance)
    content_type = ContentType.objects.get_for_model(instance)

    def table_or_none(data, table_cls, attach_instance=False):
        if not data:
            return None

        table = table_cls(data)
        table.configure(request)

        if attach_instance:
            table.instance = instance

        return table

    return {
        'zabbix_template_table': table_or_none(assignments['templates'], ZabbixTemplateAssignmentObjectViewTable),
        'zabbix_macro_table': table_or_none(assignments['macros'], ZabbixMacroAssignmentObjectViewTable, attach_instance=True),
        'zabbix_tag_table': table_or_none(assignments['tags'], ZabbixTagAssignmentObjectViewTable),
        'zabbix_hostgroup_table': table_or_none(assignments['hostgroups'], ZabbixHostgroupAssignmentObjectViewTable),
        'object': instance,
        'content_type': content_type,
    }


def _merge_direct_and_inherited(direct_list, inherited_map, key):
    direct_ids = set()
    for direct_obj in direct_list:
        direct_id = getattr(direct_obj, key)
        direct_ids.add(direct_id)

    extras = []
    for inherited_obj in inherited_map.values():
        inherited_id = getattr(inherited_obj, key)
        if inherited_id in direct_ids:
            continue
        extras.append(inherited_obj)

    return direct_list + extras


def get_assigned_zabbixobjects(instance, zabbixserver=None):
    """
    Return raw Zabbix assignment lists (direct + inherited) without any table
    formatting.

    If ``zabbixserver`` is given, results are scoped to that server:
      - Templates / Macros / Hostgroups / HostInterfaces are filtered to the
        server they belong to (see ``_INHERITANCE_MODELS`` for the exact
        traversal per model).
      - Tags, ConfigurationGroups and HostInventory have no server relation
        and are returned regardless.
    """
    content_type = ContentType.objects.get_for_model(instance)
    base = Q(assigned_object_type=content_type, assigned_object_id=instance.id)

    def direct(model, select_field, server_filter):
        qs = model.objects.filter(base).select_related(select_field)
        if zabbixserver is not None and server_filter is not None:
            qs = qs.filter(server_filter(zabbixserver))

        return qs

    direct_templates = list(direct(ZabbixTemplateAssignment, 'zabbixtemplate', _template_server_filter))
    direct_macros = list(direct(ZabbixMacroAssignment, 'zabbixmacro', _macro_server_filter))
    direct_tags = list(direct(ZabbixTagAssignment, 'zabbixtag', None))
    direct_hostgroups = list(direct(ZabbixHostgroupAssignment, 'zabbixhostgroup', _hostgroup_server_filter))

    # HostInterfaces have their own zabbixserver FK (not routed through a nested assignment), so filter it directly.
    hostinterface_qs = ZabbixHostInterface.objects.filter(base)
    if zabbixserver is not None:
        hostinterface_qs = hostinterface_qs.filter(zabbixserver_id=zabbixserver.id)

    hostinterfaces = list(hostinterface_qs)

    hostinventory = ZabbixHostInventory.objects.filter(base).first()
    configurationgroup = ZabbixConfigurationGroupAssignment.objects.filter(base).first()

    inherited = resolve_inherited_zabbix_assignments(instance, zabbixserver=zabbixserver)

    return {
        'templates': _merge_direct_and_inherited(direct_templates, inherited['templates'], 'zabbixtemplate_id'),
        'macros': _merge_direct_and_inherited(direct_macros, inherited['macros'], 'zabbixmacro_id'),
        'tags': _merge_direct_and_inherited(direct_tags, inherited['tags'], 'id'),
        'hostgroups': _merge_direct_and_inherited(direct_hostgroups, inherited['hostgroups'], 'zabbixhostgroup_id'),
        'hostinterfaces': hostinterfaces,
        'hostinventory': hostinventory,
        'configurationgroup': configurationgroup,
    }


def _walk_path(obj, path):
    """
    Follow a dotted attribute path on a model instance.

    Django caches FK lookups on the instance (in ``_state.fields_cache``),
    so sibling paths that share a prefix (e.g. ``('device',)`` and
    ``('device', 'role')``) do not re-issue the FK query.
    """

    for attr in path:
        obj = getattr(obj, attr, None)
        if obj is None:
            return None

        if isinstance(obj, (BaseManager, QuerySet)):
            obj = obj.first()
            if obj is None:
                return None

    return obj if isinstance(obj, Model) else None


def _resolve_parents(assigned_object, paths):
    """
    Walk every path once, returning ``(path, related_obj, ct_id)`` triples
    (with ``None`` for paths that don't resolve) and a ``{ct_id: {pk, ...}}``
    map for batching the assignment queries.
    """
    resolved = []
    pks_by_ct = defaultdict(set)
    ct_id_by_model = {}

    for path in paths:
        related_obj = _walk_path(assigned_object, path)
        if related_obj is None:
            resolved.append((path, None, None))
            continue

        model_cls = type(related_obj)
        ct_id = ct_id_by_model.get(model_cls)
        if ct_id is None:
            ct_id = ContentType.objects.get_for_model(model_cls).id
            ct_id_by_model[model_cls] = ct_id

        resolved.append((path, related_obj, ct_id))
        pks_by_ct[ct_id].add(related_obj.pk)

    return resolved, pks_by_ct


def _index_assignments(pks_by_ct, zabbixserver):
    """
    Fetch all inherited assignments in exactly ``len(_INHERITANCE_MODELS)``
    queries and index each result set by ``(ct_id, object_id)``.
    """
    if not pks_by_ct:
        return [defaultdict(list) for _ in _INHERITANCE_MODELS]

    parent_filter = Q()
    for ct_id, pks in pks_by_ct.items():
        parent_filter |= Q(assigned_object_type_id=ct_id, assigned_object_id__in=pks)

    indexes = []
    for model, select_field, _, server_filter in _INHERITANCE_MODELS:
        qs = model.objects.filter(parent_filter).select_related(select_field)
        if zabbixserver is not None and server_filter is not None:
            qs = qs.filter(server_filter(zabbixserver))

        idx = defaultdict(list)
        for row in qs:
            idx[(row.assigned_object_type_id, row.assigned_object_id)].append(row)

        indexes.append(idx)

    return indexes


def resolve_inherited_zabbix_assignments(assigned_object, zabbixserver=None):
    """
    Walk the configured inheritance chain and collect Zabbix assignments this
    object inherits from its parents (device → role → device_type →
    manufacturer → platform → cluster → …).

    If ``zabbixserver`` is given, results are scoped to that server. Models
    that have no server relation (tags, configuration groups) are returned
    regardless.

    Deduplication is first-write-wins in inheritance-chain order, matching
    the previous behaviour. Each returned assignment has ``_inherited_from``
    set to a human-readable path label.

    Query complexity: exactly ``len(_INHERITANCE_MODELS)`` assignment queries
    regardless of chain length, plus at most one FK query per hop in the
    chain (Django's instance-level FK cache means shared prefixes are free
    after the first walk).
    """
    pluginsettings = get_plugin_settings()
    paths = tuple(pluginsettings.inheritance_chain)

    resolved, pks_by_ct = _resolve_parents(assigned_object, paths)
    indexes = _index_assignments(pks_by_ct, zabbixserver)

    results = [OrderedDict() for _ in _INHERITANCE_MODELS]
    seen = [set() for _ in _INHERITANCE_MODELS]

    for path, related_obj, ct_id in resolved:
        if related_obj is None:
            continue

        label = PATH_LABELS.get(path, '.'.join(path))
        key = (ct_id, related_obj.pk)

        for i, (_, _, dedup_attr, _) in enumerate(_INHERITANCE_MODELS):
            for assignment in indexes[i].get(key, ()):
                dedup_value = getattr(assignment, dedup_attr)
                if dedup_value in seen[i]:
                    continue

                assignment._inherited_from = label
                results[i][dedup_value] = assignment
                seen[i].add(dedup_value)

    return dict(zip(_RESULT_KEYS, results))
