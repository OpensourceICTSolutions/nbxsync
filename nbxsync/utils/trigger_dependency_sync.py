import logging

from django.contrib.contenttypes.models import ContentType

from dcim.models import Interface
from dcim.utils import decompile_path_node

from nbxsync.models import ZabbixServerAssignment
from nbxsync.settings import get_plugin_settings
from nbxsync.utils import ZabbixConnection

logger = logging.getLogger(__name__)


def _token_set(values):
    tokens = set()
    for value in values or []:
        normalized = str(value).strip().lower()
        if normalized:
            tokens.add(normalized)
            tokens.add(normalized.replace('-', ' '))
    return tokens


def normalized_role_tokens(device):
    role = getattr(device, 'role', None)
    if not role:
        return set()

    tokens = set()
    for attr in ('name', 'slug'):
        value = getattr(role, attr, None)
        if value:
            normalized = str(value).strip().lower()
            tokens.add(normalized)
            tokens.add(normalized.replace('-', ' '))
    return tokens


def get_dependency_level(device, trigger_config=None):
    trigger_config = trigger_config or get_plugin_settings().trigger_dependencies
    role_tokens = normalized_role_tokens(device)

    for index, level in enumerate(trigger_config.levels):
        if role_tokens & _token_set(level.roles):
            return index, level

    return None, None


def get_managed_trigger_descriptions(trigger_config=None):
    trigger_config = trigger_config or get_plugin_settings().trigger_dependencies
    return {level.trigger_description for level in trigger_config.levels}


def get_server_assignments(device):
    object_ct = ContentType.objects.get_for_model(device)
    return list(
        ZabbixServerAssignment.objects.filter(
            assigned_object_type=object_ct,
            assigned_object_id=device.pk,
            sync_enabled=True,
            zabbixserver__sync_enabled=True,
        ).select_related('zabbixserver')
    )


def get_host_assignment(device):
    assignments = [assignment for assignment in get_server_assignments(device) if assignment.hostid]
    return assignments[0] if assignments else None


def get_connected_devices(device):
    devices = []
    seen_ids = set()
    remote_interface_ids = []

    interfaces = list(device.interfaces.select_related('_path').order_by('name'))
    interface_content_type_id = ContentType.objects.get_for_model(Interface).id

    for interface in interfaces:
        path = getattr(interface, '_path', None)
        if not path or not path.is_complete:
            continue

        for node in path.path[-1]:
            content_type_id, object_id = decompile_path_node(node)
            if content_type_id == interface_content_type_id:
                remote_interface_ids.append(object_id)

    remote_interfaces = Interface.objects.filter(pk__in=remote_interface_ids).select_related('device', 'device__role')
    remote_interfaces_by_id = {interface.pk: interface for interface in remote_interfaces}

    for remote_interface_id in remote_interface_ids:
        remote_interface = remote_interfaces_by_id.get(remote_interface_id)
        if not remote_interface:
            continue
        remote_device = remote_interface.device
        if not remote_device or remote_device.pk in seen_ids:
            continue

        devices.append(remote_device)
        seen_ids.add(remote_device.pk)

    return devices


def get_parent_devices(child, trigger_config=None):
    trigger_config = trigger_config or get_plugin_settings().trigger_dependencies
    child_level_index, _ = get_dependency_level(child, trigger_config=trigger_config)
    if child_level_index is None:
        return []

    parents = []
    for remote_device in get_connected_devices(child):
        remote_level_index, _ = get_dependency_level(remote_device, trigger_config=trigger_config)
        if remote_level_index is not None and remote_level_index > child_level_index:
            parents.append(remote_device)

    return parents


def get_child_devices(parent, trigger_config=None):
    trigger_config = trigger_config or get_plugin_settings().trigger_dependencies
    parent_level_index, _ = get_dependency_level(parent, trigger_config=trigger_config)
    if parent_level_index is None:
        return []

    children = []
    for remote_device in get_connected_devices(parent):
        remote_level_index, _ = get_dependency_level(remote_device, trigger_config=trigger_config)
        if remote_level_index is not None and remote_level_index < parent_level_index:
            children.append(remote_device)

    return children


def get_host_trigger(api, hostid, description):
    triggers = api.trigger.get(
        hostids=[str(hostid)],
        filter={'description': description},
        output=['triggerid', 'description'],
        selectDependencies='extend',
        expandDescription=True,
    )
    return triggers[0] if triggers else None


def build_dependency_payload(child_trigger, parent_triggerids, managed_parent_descriptions):
    dependencies = child_trigger.get('dependencies', [])
    merged = []
    seen_ids = set()
    managed_parent_descriptions = set(managed_parent_descriptions)

    for dependency in dependencies:
        dependency_id = dependency.get('triggerid')
        dependency_description = dependency.get('description')
        if not dependency_id or dependency_description in managed_parent_descriptions:
            continue
        if dependency_id in seen_ids:
            continue
        merged.append({'triggerid': dependency_id})
        seen_ids.add(dependency_id)

    for parent_triggerid in parent_triggerids:
        parent_triggerid = str(parent_triggerid)
        if parent_triggerid not in seen_ids:
            merged.append({'triggerid': parent_triggerid})
            seen_ids.add(parent_triggerid)

    return merged


def sync_device_trigger_dependencies(device):
    trigger_config = get_plugin_settings().trigger_dependencies

    if getattr(device._meta, 'model_name', None) != 'device':
        logger.debug('Skipping trigger dependency sync for unsupported object type: %s', device)
        return []

    device_level_index, _ = get_dependency_level(device, trigger_config=trigger_config)
    if device_level_index is None:
        logger.debug('Skipping trigger dependency sync for unsupported role on %s.', device)
        return []

    children_to_sync = []

    if device_level_index < len(trigger_config.levels) - 1:
        children_to_sync.append(device)

    children_to_sync.extend(get_child_devices(device, trigger_config=trigger_config))
    return _sync_child_dependencies(children_to_sync, trigger_config=trigger_config)


def _sync_child_dependencies(children, trigger_config=None):
    trigger_config = trigger_config or get_plugin_settings().trigger_dependencies
    prepared_by_server = {}

    for child in children:
        prepared = _prepare_child_dependency_sync(child, trigger_config=trigger_config)
        if not prepared:
            continue

        server_id = prepared['child_assignment'].zabbixserver_id
        prepared_by_server.setdefault(server_id, []).append(prepared)

    results = []
    for prepared_children in prepared_by_server.values():
        zabbixserver = prepared_children[0]['child_assignment'].zabbixserver
        with ZabbixConnection(zabbixserver) as api:
            for prepared in prepared_children:
                result = _sync_prepared_child_dependency(prepared, api, trigger_config=trigger_config)
                if result:
                    results.append(result)

    return results


def _prepare_child_dependency_sync(child, trigger_config=None):
    trigger_config = trigger_config or get_plugin_settings().trigger_dependencies
    child_level_index, child_level = get_dependency_level(child, trigger_config=trigger_config)
    if child_level_index is None:
        logger.debug('Skipping dependency sync for unsupported child role on %s.', child)
        return None

    parent_devices = get_parent_devices(child, trigger_config=trigger_config)
    if not parent_devices:
        logger.warning('No higher-level connected parent found for %s; skipping dependency sync.', child)
        return None

    child_assignment = get_host_assignment(child)
    if not child_assignment:
        logger.warning('No Zabbix host assignment with hostid found for %s.', child)
        return None

    return {
        'child': child,
        'child_level': child_level,
        'parent_devices': parent_devices,
        'child_assignment': child_assignment,
    }


def _sync_child_dependency(child, trigger_config=None, api=None):
    trigger_config = trigger_config or get_plugin_settings().trigger_dependencies
    prepared = _prepare_child_dependency_sync(child, trigger_config=trigger_config)
    if not prepared:
        return None

    if api is not None:
        return _sync_prepared_child_dependency(prepared, api, trigger_config=trigger_config)

    with ZabbixConnection(prepared['child_assignment'].zabbixserver) as connection:
        return _sync_prepared_child_dependency(prepared, connection, trigger_config=trigger_config)


def _sync_prepared_child_dependency(prepared, api, trigger_config=None):
    trigger_config = trigger_config or get_plugin_settings().trigger_dependencies
    child = prepared['child']
    child_level = prepared['child_level']
    parent_devices = prepared['parent_devices']
    child_assignment = prepared['child_assignment']

    child_trigger = get_host_trigger(api, child_assignment.hostid, child_level.trigger_description)
    if not child_trigger:
        logger.warning('No "%s" trigger found for %s.', child_level.trigger_description, child)
        return None

    parent_triggers = []
    parent_names = []
    for parent in parent_devices:
        _, parent_level = get_dependency_level(parent, trigger_config=trigger_config)
        parent_assignment = get_host_assignment(parent)
        if not parent_assignment:
            logger.warning('No Zabbix host assignment with hostid found for parent %s.', parent)
            continue

        if child_assignment.zabbixserver_id != parent_assignment.zabbixserver_id:
            logger.warning(
                'Skipping dependency sync for %s: child and parent %s are assigned to different Zabbix servers.',
                child,
                parent,
            )
            continue

        parent_trigger = get_host_trigger(api, parent_assignment.hostid, parent_level.trigger_description)
        if not parent_trigger:
            logger.warning('No "%s" trigger found for %s.', parent_level.trigger_description, parent)
            continue

        parent_triggers.append(parent_trigger)
        parent_names.append(str(parent))

    if not parent_triggers:
        return None

    dependency_payload = build_dependency_payload(
        child_trigger,
        [trigger['triggerid'] for trigger in parent_triggers],
        get_managed_trigger_descriptions(trigger_config=trigger_config),
    )
    current_ids = {dep.get('triggerid') for dep in child_trigger.get('dependencies', []) if dep.get('triggerid')}
    desired_ids = {dep.get('triggerid') for dep in dependency_payload}

    if current_ids == desired_ids:
        logger.info('Dependency already correct: %s -> %s.', child, ', '.join(parent_names))
        return {'child': str(child), 'parent': ', '.join(parent_names), 'changed': False}

    api.trigger.update(triggerid=child_trigger['triggerid'], dependencies=dependency_payload)
    logger.info('Updated dependency: %s -> %s.', child, ', '.join(parent_names))
    return {'child': str(child), 'parent': ', '.join(parent_names), 'changed': True}
