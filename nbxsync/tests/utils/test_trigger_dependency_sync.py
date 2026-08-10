from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import TestCase

from nbxsync.settings import PluginSettingsModel
from nbxsync.utils.trigger_dependency_sync import (
    _prepare_child_dependency_sync,
    _sync_child_dependencies,
    _sync_prepared_child_dependency,
    _token_set,
    build_dependency_payload,
    get_child_devices,
    get_connected_devices,
    get_dependency_level,
    get_host_assignments,
    get_host_trigger,
    get_managed_trigger_descriptions,
    get_parent_devices,
    get_server_assignments,
    normalized_role_tokens,
    sync_device_trigger_dependencies,
)


class TriggerDependencySyncTestCase(TestCase):
    def setUp(self):
        self.trigger_config = PluginSettingsModel().trigger_dependencies

    def test_normalized_role_tokens_reads_name_and_slug(self):
        device = SimpleNamespace(role=SimpleNamespace(name='Branch Gateway', slug='branch-gateway'))

        self.assertEqual(normalized_role_tokens(device), {'branch gateway', 'branch-gateway'})

    def test_role_matching_uses_configured_level_tokens(self):
        access_point = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))
        switch = SimpleNamespace(role=SimpleNamespace(name='Switch', slug='switch'))
        gateway = SimpleNamespace(role=SimpleNamespace(name='Gateway', slug='gateway'))
        firewall = SimpleNamespace(role=SimpleNamespace(name='Firewall', slug='firewall'))
        router = SimpleNamespace(role=SimpleNamespace(name='Router', slug='router'))

        access_point_index, access_point_level = get_dependency_level(access_point, trigger_config=self.trigger_config)
        switch_index, switch_level = get_dependency_level(switch, trigger_config=self.trigger_config)
        gateway_index, gateway_level = get_dependency_level(gateway, trigger_config=self.trigger_config)
        firewall_index, firewall_level = get_dependency_level(firewall, trigger_config=self.trigger_config)
        router_index, router_level = get_dependency_level(router, trigger_config=self.trigger_config)

        self.assertEqual((access_point_index, access_point_level.name), (0, 'access_point'))
        self.assertEqual((switch_index, switch_level.name), (1, 'switch'))
        self.assertEqual((gateway_index, gateway_level.name), (2, 'gateway'))
        self.assertEqual((firewall_index, firewall_level.name), (2, 'gateway'))
        self.assertEqual((router_index, router_level.name), (2, 'gateway'))

    def test_build_dependency_payload_preserves_unmanaged_dependencies(self):
        child_trigger = {
            'triggerid': '100',
            'dependencies': [
                {'triggerid': '200', 'description': 'Unrelated dependency'},
                {'triggerid': '201', 'description': self.trigger_config.levels[1].trigger_description},
            ],
        }

        payload = build_dependency_payload(child_trigger, ['300'], {self.trigger_config.levels[1].trigger_description})

        self.assertEqual(payload, [{'triggerid': '200'}, {'triggerid': '300'}])

    def test_build_dependency_payload_deduplicates_parent_dependencies(self):
        child_trigger = {
            'triggerid': '100',
            'dependencies': [
                {'triggerid': '300', 'description': 'Unrelated dependency'},
            ],
        }

        payload = build_dependency_payload(child_trigger, ['300'], set())

        self.assertEqual(payload, [{'triggerid': '300'}])

    @patch('nbxsync.utils.trigger_dependency_sync.Interface.objects')
    @patch('nbxsync.utils.trigger_dependency_sync.ContentType.objects.get_for_model')
    def test_get_connected_devices_bulk_fetches_remote_interfaces(self, mock_get_content_type, mock_interface_objects):
        interface_content_type_id = 10
        remote_interface_id = 101
        remote_device = SimpleNamespace(pk=201)
        remote_interface = SimpleNamespace(pk=remote_interface_id, device=remote_device)
        path = SimpleNamespace(
            is_complete=True,
            path=[
                [f'{interface_content_type_id}:1'],
                ['11:50'],
                [f'{interface_content_type_id}:{remote_interface_id}'],
            ],
        )
        local_interface = SimpleNamespace(pk=1, _path=path)
        device = SimpleNamespace(interfaces=FakeInterfaceManager([local_interface]))
        mock_get_content_type.return_value = SimpleNamespace(id=interface_content_type_id)
        mock_interface_objects.filter.return_value.select_related.return_value = [remote_interface]

        self.assertEqual(get_connected_devices(device), [remote_device])
        mock_interface_objects.filter.assert_called_once_with(pk__in=[remote_interface_id])
        mock_interface_objects.filter.return_value.select_related.assert_called_once_with('device', 'device__role')

    @patch('nbxsync.utils.trigger_dependency_sync.get_child_devices', return_value=[])
    @patch('nbxsync.utils.trigger_dependency_sync._sync_child_dependencies', return_value=[{'child': 'ap', 'changed': True}])
    @patch('nbxsync.utils.trigger_dependency_sync.get_plugin_settings')
    def test_sync_device_trigger_dependencies_syncs_lowest_level_device(self, mock_settings, mock_sync_children, _mock_get_children):
        self.trigger_config.enabled = True
        mock_settings.return_value = SimpleNamespace(trigger_dependencies=self.trigger_config)
        access_point = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'), _meta=SimpleNamespace(model_name='device'))

        result = sync_device_trigger_dependencies(access_point)

        self.assertEqual(result, [{'child': 'ap', 'changed': True}])
        mock_sync_children.assert_called_once_with([access_point], trigger_config=self.trigger_config)

    @patch('nbxsync.utils.trigger_dependency_sync.ZabbixConnection')
    @patch('nbxsync.utils.trigger_dependency_sync.get_host_assignments')
    @patch('nbxsync.utils.trigger_dependency_sync.get_parent_devices')
    @patch('nbxsync.utils.trigger_dependency_sync.get_child_devices')
    @patch('nbxsync.utils.trigger_dependency_sync.get_plugin_settings')
    def test_sync_device_trigger_dependencies_reuses_connection_per_zabbix_server(self, mock_settings, mock_get_children, mock_get_parents, mock_get_assignments, mock_connection):
        """All devices on one shared server → single ZabbixConnection reused across children."""
        self.trigger_config.enabled = True
        mock_settings.return_value = SimpleNamespace(trigger_dependencies=self.trigger_config)

        zabbixserver = SimpleNamespace(name='Zabbix 1')
        gateway = SimpleNamespace(role=SimpleNamespace(name='Gateway', slug='gateway'), _meta=SimpleNamespace(model_name='device'))
        child_1 = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))
        child_2 = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))
        child_1_assignment = SimpleNamespace(hostid='101', zabbixserver_id=1, zabbixserver=zabbixserver)
        child_2_assignment = SimpleNamespace(hostid='102', zabbixserver_id=1, zabbixserver=zabbixserver)
        parent_assignment = SimpleNamespace(hostid='201', zabbixserver_id=1, zabbixserver=zabbixserver)

        mock_get_children.return_value = [child_1, child_2]
        mock_get_parents.return_value = [gateway]

        def assignments_for(device):
            if device is child_1:
                return {1: child_1_assignment}
            if device is child_2:
                return {1: child_2_assignment}
            if device is gateway:
                return {1: parent_assignment}

        mock_get_assignments.side_effect = assignments_for

        api = MagicMock()
        mock_connection.return_value.__enter__.return_value = api

        def trigger_for(_api, hostid, description):
            if description == 'AP status':
                return {'triggerid': f'child-{hostid}', 'description': description, 'dependencies': []}
            return {'triggerid': f'parent-{hostid}', 'description': description, 'dependencies': []}

        with patch('nbxsync.utils.trigger_dependency_sync.get_host_trigger', side_effect=trigger_for):
            result = sync_device_trigger_dependencies(gateway)

        mock_connection.assert_called_once_with(zabbixserver)
        self.assertEqual(api.trigger.update.call_count, 2)
        self.assertEqual(
            result,
            [
                {'child': str(child_1), 'parent': str(gateway), 'server': str(zabbixserver), 'changed': True},
                {'child': str(child_2), 'parent': str(gateway), 'server': str(zabbixserver), 'changed': True},
            ],
        )

    @patch('nbxsync.utils.trigger_dependency_sync.ZabbixConnection')
    @patch('nbxsync.utils.trigger_dependency_sync.get_host_assignments')
    @patch('nbxsync.utils.trigger_dependency_sync.get_parent_devices')
    @patch('nbxsync.utils.trigger_dependency_sync.get_child_devices')
    @patch('nbxsync.utils.trigger_dependency_sync.get_plugin_settings')
    def test_sync_uses_a_connection_per_shared_zabbix_server(self, mock_settings, mock_get_children, mock_get_parents, mock_get_assignments, mock_connection):
        """Child and parent both assigned to servers A and B → one connection per server, both updated."""
        self.trigger_config.enabled = True
        mock_settings.return_value = SimpleNamespace(trigger_dependencies=self.trigger_config)

        server_a = SimpleNamespace(name='Zabbix A')
        server_b = SimpleNamespace(name='Zabbix B')

        gateway = SimpleNamespace(role=SimpleNamespace(name='Gateway', slug='gateway'), _meta=SimpleNamespace(model_name='device'))
        access_point = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))

        ap_assignment_a = SimpleNamespace(hostid='101', zabbixserver_id=1, zabbixserver=server_a)
        ap_assignment_b = SimpleNamespace(hostid='102', zabbixserver_id=2, zabbixserver=server_b)
        gw_assignment_a = SimpleNamespace(hostid='201', zabbixserver_id=1, zabbixserver=server_a)
        gw_assignment_b = SimpleNamespace(hostid='202', zabbixserver_id=2, zabbixserver=server_b)

        mock_get_children.return_value = [access_point]
        mock_get_parents.return_value = [gateway]

        def assignments_for(device):
            if device is access_point:
                return {1: ap_assignment_a, 2: ap_assignment_b}
            if device is gateway:
                return {1: gw_assignment_a, 2: gw_assignment_b}

        mock_get_assignments.side_effect = assignments_for

        connections_by_server_name = {}

        def connection_factory(server):
            api = MagicMock()
            connections_by_server_name[server.name] = api
            cm = MagicMock()
            cm.__enter__.return_value = api
            return cm

        mock_connection.side_effect = connection_factory

        def trigger_for(_api, hostid, description):
            if description == 'AP status':
                return {'triggerid': f'child-{hostid}', 'description': description, 'dependencies': []}
            return {'triggerid': f'parent-{hostid}', 'description': description, 'dependencies': []}

        with patch('nbxsync.utils.trigger_dependency_sync.get_host_trigger', side_effect=trigger_for):
            result = sync_device_trigger_dependencies(gateway)

        self.assertEqual(mock_connection.call_count, 2)
        connected_server_names = {call.args[0].name for call in mock_connection.call_args_list}
        self.assertEqual(connected_server_names, {'Zabbix A', 'Zabbix B'})

        self.assertEqual(connections_by_server_name['Zabbix A'].trigger.update.call_count, 1)
        self.assertEqual(connections_by_server_name['Zabbix B'].trigger.update.call_count, 1)

        connections_by_server_name['Zabbix A'].trigger.update.assert_called_once_with(triggerid='child-101', dependencies=[{'triggerid': 'parent-201'}])
        connections_by_server_name['Zabbix B'].trigger.update.assert_called_once_with(triggerid='child-102', dependencies=[{'triggerid': 'parent-202'}])

        self.assertEqual(len(result), 2)
        self.assertTrue(all(entry['changed'] for entry in result))

    @patch('nbxsync.utils.trigger_dependency_sync.ZabbixConnection')
    @patch('nbxsync.utils.trigger_dependency_sync.get_host_assignments')
    @patch('nbxsync.utils.trigger_dependency_sync.get_parent_devices')
    @patch('nbxsync.utils.trigger_dependency_sync.get_child_devices')
    @patch('nbxsync.utils.trigger_dependency_sync.get_plugin_settings')
    def test_sync_skips_server_where_no_parent_is_assigned(self, mock_settings, mock_get_children, mock_get_parents, mock_get_assignments, mock_connection):
        """Child on {A, B} but parent only on {A} → sync runs on A only, warning logged for B."""
        self.trigger_config.enabled = True
        mock_settings.return_value = SimpleNamespace(trigger_dependencies=self.trigger_config)

        server_a = SimpleNamespace(name='Zabbix A')
        server_b = SimpleNamespace(name='Zabbix B')

        gateway = SimpleNamespace(role=SimpleNamespace(name='Gateway', slug='gateway'), _meta=SimpleNamespace(model_name='device'))
        access_point = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))

        ap_assignment_a = SimpleNamespace(hostid='101', zabbixserver_id=1, zabbixserver=server_a)
        ap_assignment_b = SimpleNamespace(hostid='102', zabbixserver_id=2, zabbixserver=server_b)
        gw_assignment_a = SimpleNamespace(hostid='201', zabbixserver_id=1, zabbixserver=server_a)

        mock_get_children.return_value = [access_point]
        mock_get_parents.return_value = [gateway]

        def assignments_for(device):
            if device is access_point:
                return {1: ap_assignment_a, 2: ap_assignment_b}
            if device is gateway:
                return {1: gw_assignment_a}

        mock_get_assignments.side_effect = assignments_for

        api = MagicMock()
        mock_connection.return_value.__enter__.return_value = api

        def trigger_for(_api, hostid, description):
            if description == 'AP status':
                return {'triggerid': f'child-{hostid}', 'description': description, 'dependencies': []}
            return {'triggerid': f'parent-{hostid}', 'description': description, 'dependencies': []}

        with patch('nbxsync.utils.trigger_dependency_sync.get_host_trigger', side_effect=trigger_for):
            with self.assertLogs('nbxsync.utils.trigger_dependency_sync', level='WARNING') as log_ctx:
                result = sync_device_trigger_dependencies(gateway)

        mock_connection.assert_called_once_with(server_a)
        api.trigger.update.assert_called_once_with(triggerid='child-101', dependencies=[{'triggerid': 'parent-201'}])

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]['changed'])

        warning_text = '\n'.join(log_ctx.output)
        self.assertNotIn('Zabbix A', warning_text)  # server A synced successfully; no warning about it
        self.assertTrue(any('server' in line.lower() and 'Zabbix B' in line for line in log_ctx.output), f'expected a warning naming server B; got: {log_ctx.output}')

    @patch('nbxsync.utils.trigger_dependency_sync.ZabbixConnection')
    @patch('nbxsync.utils.trigger_dependency_sync._sync_prepared_child_dependency')
    @patch('nbxsync.utils.trigger_dependency_sync.get_host_assignments')
    @patch('nbxsync.utils.trigger_dependency_sync.get_parent_devices')
    @patch('nbxsync.utils.trigger_dependency_sync.get_child_devices')
    @patch('nbxsync.utils.trigger_dependency_sync.get_plugin_settings')
    def test_sync_isolates_child_failure_on_same_server(self, mock_settings, mock_get_children, mock_get_parents, mock_get_assignments, mock_sync_prepared, mock_connection):
        """Two children on one server, first raises → second still syncs, error logged, no exception propagates."""
        self.trigger_config.enabled = True
        mock_settings.return_value = SimpleNamespace(trigger_dependencies=self.trigger_config)

        zabbixserver = SimpleNamespace(name='Zabbix 1')
        gateway = SimpleNamespace(role=SimpleNamespace(name='Gateway', slug='gateway'), _meta=SimpleNamespace(model_name='device'))
        child_1 = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))
        child_2 = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))
        child_1_assignment = SimpleNamespace(hostid='101', zabbixserver_id=1, zabbixserver=zabbixserver)
        child_2_assignment = SimpleNamespace(hostid='102', zabbixserver_id=1, zabbixserver=zabbixserver)
        parent_assignment = SimpleNamespace(hostid='201', zabbixserver_id=1, zabbixserver=zabbixserver)

        mock_get_children.return_value = [child_1, child_2]
        mock_get_parents.return_value = [gateway]

        def assignments_for(device):
            if device is child_1:
                return {1: child_1_assignment}
            if device is child_2:
                return {1: child_2_assignment}
            if device is gateway:
                return {1: parent_assignment}

        mock_get_assignments.side_effect = assignments_for

        api = MagicMock()
        mock_connection.return_value.__enter__.return_value = api

        child_2_result = {'child': str(child_2), 'parent': str(gateway), 'server': str(zabbixserver), 'changed': True}
        mock_sync_prepared.side_effect = [Exception('Zabbix API timeout on child 1'), child_2_result]

        with self.assertLogs('nbxsync.utils.trigger_dependency_sync', level='WARNING') as log_ctx:
            result = sync_device_trigger_dependencies(gateway)

        mock_connection.assert_called_once_with(zabbixserver)
        self.assertEqual(mock_sync_prepared.call_count, 2)  # second child still attempted after first failure
        self.assertEqual(result, [child_2_result])  # only successful child appears in result

        log_text = '\n'.join(log_ctx.output)
        self.assertIn('Zabbix API timeout on child 1', log_text)

    @patch('nbxsync.utils.trigger_dependency_sync.ZabbixConnection')
    @patch('nbxsync.utils.trigger_dependency_sync.get_host_assignments')
    @patch('nbxsync.utils.trigger_dependency_sync.get_parent_devices')
    @patch('nbxsync.utils.trigger_dependency_sync.get_child_devices')
    @patch('nbxsync.utils.trigger_dependency_sync.get_plugin_settings')
    def test_sync_isolates_failure_of_one_zabbix_server(self, mock_settings, mock_get_children, mock_get_parents, mock_get_assignments, mock_connection):
        """One Zabbix server refusing connection doesn't stop sync on the other server."""
        self.trigger_config.enabled = True
        mock_settings.return_value = SimpleNamespace(trigger_dependencies=self.trigger_config)

        server_a = SimpleNamespace(name='Zabbix A')
        server_b = SimpleNamespace(name='Zabbix B')

        gateway = SimpleNamespace(role=SimpleNamespace(name='Gateway', slug='gateway'), _meta=SimpleNamespace(model_name='device'))
        access_point = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))

        ap_assignment_a = SimpleNamespace(hostid='101', zabbixserver_id=1, zabbixserver=server_a)
        ap_assignment_b = SimpleNamespace(hostid='102', zabbixserver_id=2, zabbixserver=server_b)
        gw_assignment_a = SimpleNamespace(hostid='201', zabbixserver_id=1, zabbixserver=server_a)
        gw_assignment_b = SimpleNamespace(hostid='202', zabbixserver_id=2, zabbixserver=server_b)

        mock_get_children.return_value = [access_point]
        mock_get_parents.return_value = [gateway]

        def assignments_for(device):
            if device is access_point:
                return {1: ap_assignment_a, 2: ap_assignment_b}
            if device is gateway:
                return {1: gw_assignment_a, 2: gw_assignment_b}

        mock_get_assignments.side_effect = assignments_for

        server_b_api = MagicMock()

        def connection_factory(server):
            if server is server_a:
                raise Exception('Zabbix A unreachable')
            cm = MagicMock()
            cm.__enter__.return_value = server_b_api
            return cm

        mock_connection.side_effect = connection_factory

        def trigger_for(_api, hostid, description):
            if description == 'AP status':
                return {'triggerid': f'child-{hostid}', 'description': description, 'dependencies': []}
            return {'triggerid': f'parent-{hostid}', 'description': description, 'dependencies': []}

        with patch('nbxsync.utils.trigger_dependency_sync.get_host_trigger', side_effect=trigger_for):
            with self.assertLogs('nbxsync.utils.trigger_dependency_sync', level='WARNING') as log_ctx:
                result = sync_device_trigger_dependencies(gateway)

        # Both servers were attempted (mock records the call even when it raises)
        self.assertEqual(mock_connection.call_count, 2)
        connected_server_names = [call.args[0].name for call in mock_connection.call_args_list]
        self.assertIn('Zabbix A', connected_server_names)
        self.assertIn('Zabbix B', connected_server_names)

        # Only server B produced an update
        server_b_api.trigger.update.assert_called_once_with(triggerid='child-102', dependencies=[{'triggerid': 'parent-202'}])

        # Only server B contributed to results
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['server'], str(server_b))

        # Server A's failure was logged
        log_text = '\n'.join(log_ctx.output)
        self.assertIn('Zabbix A unreachable', log_text)

    def test_token_and_role_normalization_edge_cases(self):
        self.assertEqual(_token_set(None), set())
        self.assertEqual(_token_set([' Branch-Gateway ', '', '   ']), {'branch-gateway', 'branch gateway'})
        self.assertEqual(normalized_role_tokens(SimpleNamespace(role=None)), set())
        self.assertEqual(normalized_role_tokens(SimpleNamespace(role=SimpleNamespace(name=None, slug=' Branch-Gateway '))), {'branch-gateway', 'branch gateway'})

    @patch('nbxsync.utils.trigger_dependency_sync.get_plugin_settings')
    def test_dependency_level_and_managed_descriptions_use_default_settings(self, mock_settings):
        mock_settings.return_value = SimpleNamespace(trigger_dependencies=self.trigger_config)
        access_point = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))
        unsupported = SimpleNamespace(role=SimpleNamespace(name='Load Balancer', slug='load-balancer'))

        level_index, level = get_dependency_level(access_point)

        self.assertEqual((level_index, level.name), (0, 'access_point'))
        self.assertEqual(get_dependency_level(unsupported), (None, None))
        self.assertEqual(get_managed_trigger_descriptions(), {level.trigger_description for level in self.trigger_config.levels})

    @patch('nbxsync.utils.trigger_dependency_sync.ZabbixServerAssignment.objects')
    @patch('nbxsync.utils.trigger_dependency_sync.ContentType.objects.get_for_model')
    def test_get_server_assignments_filters_and_selects_server(self, mock_get_content_type, mock_assignment_objects):
        device = SimpleNamespace(pk=42)
        content_type = SimpleNamespace(pk=7)
        assignment = SimpleNamespace(hostid='1001')
        mock_get_content_type.return_value = content_type
        queryset = mock_assignment_objects.filter.return_value
        queryset.select_related.return_value = [assignment]

        result = get_server_assignments(device)

        self.assertEqual(result, [assignment])
        mock_assignment_objects.filter.assert_called_once_with(assigned_object_type=content_type, assigned_object_id=42, sync_enabled=True, zabbixserver__sync_enabled=True)
        queryset.select_related.assert_called_once_with('zabbixserver')

    @patch('nbxsync.utils.trigger_dependency_sync.get_server_assignments')
    def test_get_host_assignments_skips_missing_hostids_and_keys_by_server(self, mock_get_server_assignments):
        no_hostid = SimpleNamespace(hostid='', zabbixserver_id=1)
        first = SimpleNamespace(hostid='101', zabbixserver_id=2)
        replacement = SimpleNamespace(hostid='102', zabbixserver_id=2)
        mock_get_server_assignments.return_value = [no_hostid, first, replacement]

        result = get_host_assignments(SimpleNamespace())

        self.assertEqual(result, {2: replacement})

    @patch('nbxsync.utils.trigger_dependency_sync.Interface.objects')
    @patch('nbxsync.utils.trigger_dependency_sync.ContentType.objects.get_for_model')
    def test_get_connected_devices_skips_invalid_paths_missing_interfaces_and_duplicate_devices(self, mock_get_content_type, mock_interface_objects):
        interface_content_type_id = 10
        remote_device = SimpleNamespace(pk=201)
        remote_interface = SimpleNamespace(pk=101, device=remote_device)
        remote_without_device = SimpleNamespace(pk=102, device=None)

        interfaces = [
            SimpleNamespace(pk=1),
            SimpleNamespace(pk=2, _path=SimpleNamespace(is_complete=False, path=[])),
            SimpleNamespace(
                pk=3,
                _path=SimpleNamespace(
                    is_complete=True,
                    path=[['ignored'], ['10:101', '11:999', '10:102', '10:103', '10:101']],
                ),
            ),
        ]
        device = SimpleNamespace(interfaces=FakeInterfaceManager(interfaces))
        mock_get_content_type.return_value = SimpleNamespace(id=interface_content_type_id)
        mock_interface_objects.filter.return_value.select_related.return_value = [remote_interface, remote_without_device]

        result = get_connected_devices(device)

        self.assertEqual(result, [remote_device])
        mock_interface_objects.filter.assert_called_once_with(pk__in=[101, 102, 103, 101])

    @patch('nbxsync.utils.trigger_dependency_sync.get_connected_devices')
    @patch('nbxsync.utils.trigger_dependency_sync.get_plugin_settings')
    def test_get_parent_devices_filters_by_higher_dependency_level(self, mock_settings, mock_get_connected):
        mock_settings.return_value = SimpleNamespace(trigger_dependencies=self.trigger_config)
        switch = SimpleNamespace(role=SimpleNamespace(name='Switch', slug='switch'))
        access_point = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))
        peer_switch = SimpleNamespace(role=SimpleNamespace(name='Switch', slug='switch'))
        gateway = SimpleNamespace(role=SimpleNamespace(name='Gateway', slug='gateway'))
        unsupported = SimpleNamespace(role=SimpleNamespace(name='Load Balancer', slug='load-balancer'))
        mock_get_connected.return_value = [access_point, peer_switch, gateway, unsupported]

        self.assertEqual(get_parent_devices(switch), [gateway])

        unsupported_child = SimpleNamespace(role=SimpleNamespace(name='Load Balancer', slug='load-balancer'))
        mock_get_connected.reset_mock()
        self.assertEqual(get_parent_devices(unsupported_child, trigger_config=self.trigger_config), [])
        mock_get_connected.assert_not_called()

    @patch('nbxsync.utils.trigger_dependency_sync.get_connected_devices')
    @patch('nbxsync.utils.trigger_dependency_sync.get_plugin_settings')
    def test_get_child_devices_filters_by_lower_dependency_level(self, mock_settings, mock_get_connected):
        mock_settings.return_value = SimpleNamespace(trigger_dependencies=self.trigger_config)
        switch = SimpleNamespace(role=SimpleNamespace(name='Switch', slug='switch'))
        access_point = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))
        peer_switch = SimpleNamespace(role=SimpleNamespace(name='Switch', slug='switch'))
        gateway = SimpleNamespace(role=SimpleNamespace(name='Gateway', slug='gateway'))
        unsupported = SimpleNamespace(role=SimpleNamespace(name='Load Balancer', slug='load-balancer'))
        mock_get_connected.return_value = [access_point, peer_switch, gateway, unsupported]

        self.assertEqual(get_child_devices(switch), [access_point])

        unsupported_parent = SimpleNamespace(role=SimpleNamespace(name='Load Balancer', slug='load-balancer'))
        mock_get_connected.reset_mock()
        self.assertEqual(get_child_devices(unsupported_parent, trigger_config=self.trigger_config), [])
        mock_get_connected.assert_not_called()

    def test_get_host_trigger_returns_first_match_or_none(self):
        api = MagicMock()
        api.trigger.get.side_effect = [[{'triggerid': '123', 'description': 'AP status'}], []]

        found = get_host_trigger(api, 101, 'AP status')
        missing = get_host_trigger(api, '102', 'AP status')

        self.assertEqual(found, {'triggerid': '123', 'description': 'AP status'})
        self.assertIsNone(missing)
        api.trigger.get.assert_any_call(hostids=['101'], filter={'description': 'AP status'}, output=['triggerid', 'description'], selectDependencies='extend', expandDescription=True)

    def test_build_dependency_payload_handles_missing_duplicate_and_managed_dependencies(self):
        managed_description = self.trigger_config.levels[1].trigger_description
        child_trigger = {
            'dependencies': [
                {'description': 'missing trigger id'},
                {'triggerid': '200', 'description': managed_description},
                {'triggerid': '201', 'description': 'Unmanaged'},
                {'triggerid': '201', 'description': 'Duplicate unmanaged'},
            ]
        }

        payload = build_dependency_payload(child_trigger, [201, 300, 300], {managed_description})

        self.assertEqual(payload, [{'triggerid': '201'}, {'triggerid': '300'}])
        self.assertEqual(build_dependency_payload({}, [], set()), [])

    @patch('nbxsync.utils.trigger_dependency_sync._sync_child_dependencies')
    @patch('nbxsync.utils.trigger_dependency_sync.get_child_devices')
    @patch('nbxsync.utils.trigger_dependency_sync.get_plugin_settings')
    def test_sync_device_trigger_dependencies_skips_unsupported_objects_and_roles(self, mock_settings, mock_get_children, mock_sync_children):
        mock_settings.return_value = SimpleNamespace(trigger_dependencies=self.trigger_config)
        unsupported_object = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'), _meta=SimpleNamespace(model_name='interface'))
        unsupported_role = SimpleNamespace(role=SimpleNamespace(name='Load Balancer', slug='load-balancer'), _meta=SimpleNamespace(model_name='device'))

        self.assertEqual(sync_device_trigger_dependencies(unsupported_object), [])
        self.assertEqual(sync_device_trigger_dependencies(unsupported_role), [])
        mock_get_children.assert_not_called()
        mock_sync_children.assert_not_called()

    @patch('nbxsync.utils.trigger_dependency_sync._sync_child_dependencies', return_value=[])
    @patch('nbxsync.utils.trigger_dependency_sync.get_child_devices')
    @patch('nbxsync.utils.trigger_dependency_sync.get_plugin_settings')
    def test_sync_device_trigger_dependencies_does_not_sync_top_level_device_as_child(self, mock_settings, mock_get_children, mock_sync_children):
        mock_settings.return_value = SimpleNamespace(trigger_dependencies=self.trigger_config)
        gateway = SimpleNamespace(role=SimpleNamespace(name='Gateway', slug='gateway'), _meta=SimpleNamespace(model_name='device'))
        child = SimpleNamespace(role=SimpleNamespace(name='Switch', slug='switch'))
        mock_get_children.return_value = [child]

        sync_device_trigger_dependencies(gateway)

        mock_sync_children.assert_called_once_with([child], trigger_config=self.trigger_config)

    @patch('nbxsync.utils.trigger_dependency_sync.ZabbixConnection')
    @patch('nbxsync.utils.trigger_dependency_sync._sync_prepared_child_dependency', return_value=None)
    @patch('nbxsync.utils.trigger_dependency_sync._prepare_child_dependency_sync')
    @patch('nbxsync.utils.trigger_dependency_sync.get_plugin_settings')
    def test_sync_child_dependencies_uses_default_settings_and_ignores_empty_results(self, mock_settings, mock_prepare, mock_sync_prepared, mock_connection):
        mock_settings.return_value = SimpleNamespace(trigger_dependencies=self.trigger_config)
        child = SimpleNamespace(name='child')
        server = SimpleNamespace(name='Zabbix')
        assignment = SimpleNamespace(zabbixserver_id=1, zabbixserver=server)
        prepared = {'child': child, 'child_assignment': assignment}
        mock_prepare.return_value = [prepared]
        api = MagicMock()
        mock_connection.return_value.__enter__.return_value = api

        self.assertEqual(_sync_child_dependencies([child]), [])
        mock_prepare.assert_called_once_with(child, trigger_config=self.trigger_config)
        mock_sync_prepared.assert_called_once_with(prepared, api, trigger_config=self.trigger_config)

    @patch('nbxsync.utils.trigger_dependency_sync.get_host_assignments')
    @patch('nbxsync.utils.trigger_dependency_sync.get_parent_devices')
    @patch('nbxsync.utils.trigger_dependency_sync.get_plugin_settings')
    def test_prepare_child_dependency_sync_defensive_exits(self, mock_settings, mock_get_parents, mock_get_assignments):
        mock_settings.return_value = SimpleNamespace(trigger_dependencies=self.trigger_config)
        unsupported = SimpleNamespace(role=SimpleNamespace(name='Load Balancer', slug='load-balancer'))
        access_point = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))
        parent = SimpleNamespace(role=SimpleNamespace(name='Gateway', slug='gateway'))

        self.assertEqual(_prepare_child_dependency_sync(unsupported), [])

        mock_get_parents.return_value = []
        self.assertEqual(_prepare_child_dependency_sync(access_point, trigger_config=self.trigger_config), [])

        mock_get_parents.return_value = [parent]
        mock_get_assignments.return_value = {}
        self.assertEqual(_prepare_child_dependency_sync(access_point, trigger_config=self.trigger_config), [])

    @patch('nbxsync.utils.trigger_dependency_sync.get_host_assignments')
    @patch('nbxsync.utils.trigger_dependency_sync.get_parent_devices')
    def test_prepare_child_dependency_sync_skips_parents_without_assignments(self, mock_get_parents, mock_get_assignments):
        access_point = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))
        parent_without_assignment = SimpleNamespace(role=SimpleNamespace(name='Switch', slug='switch'))
        child_assignment = SimpleNamespace(hostid='101', zabbixserver_id=1, zabbixserver=SimpleNamespace(name='Zabbix'))
        mock_get_parents.return_value = [parent_without_assignment]

        def assignments_for(device):
            if device is access_point:
                return {1: child_assignment}
            return {}

        mock_get_assignments.side_effect = assignments_for

        self.assertEqual(_prepare_child_dependency_sync(access_point, trigger_config=self.trigger_config), [])

    @patch('nbxsync.utils.trigger_dependency_sync.get_host_trigger', return_value=None)
    @patch('nbxsync.utils.trigger_dependency_sync.get_plugin_settings')
    def test_sync_prepared_child_dependency_returns_none_when_child_trigger_missing(self, mock_settings, mock_get_trigger):
        mock_settings.return_value = SimpleNamespace(trigger_dependencies=self.trigger_config)
        child = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))
        assignment = SimpleNamespace(hostid='101', zabbixserver=SimpleNamespace(name='Zabbix'))
        prepared = {
            'child': child,
            'child_level': self.trigger_config.levels[0],
            'child_assignment': assignment,
            'parents_on_server': [],
        }

        api = MagicMock()
        self.assertIsNone(_sync_prepared_child_dependency(prepared, api))
        mock_get_trigger.assert_called_once_with(api, '101', self.trigger_config.levels[0].trigger_description)

    @patch('nbxsync.utils.trigger_dependency_sync.get_host_trigger')
    def test_sync_prepared_child_dependency_skips_missing_parent_triggers(self, mock_get_trigger):
        child = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))
        parent = SimpleNamespace(role=SimpleNamespace(name='Switch', slug='switch'))
        assignment = SimpleNamespace(hostid='101', zabbixserver=SimpleNamespace(name='Zabbix'))
        parent_assignment = SimpleNamespace(hostid='201')
        child_trigger = {'triggerid': '100', 'description': self.trigger_config.levels[0].trigger_description, 'dependencies': []}
        mock_get_trigger.side_effect = [child_trigger, None]
        prepared = {
            'child': child,
            'child_level': self.trigger_config.levels[0],
            'child_assignment': assignment,
            'parents_on_server': [(parent, parent_assignment)],
        }

        self.assertIsNone(_sync_prepared_child_dependency(prepared, MagicMock(), trigger_config=self.trigger_config))

    @patch('nbxsync.utils.trigger_dependency_sync.get_host_trigger')
    def test_sync_prepared_child_dependency_avoids_update_when_dependency_is_already_correct(self, mock_get_trigger):
        child = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))
        parent = SimpleNamespace(role=SimpleNamespace(name='Switch', slug='switch'))
        server = SimpleNamespace(name='Zabbix')
        assignment = SimpleNamespace(hostid='101', zabbixserver=server)
        parent_assignment = SimpleNamespace(hostid='201')
        parent_description = self.trigger_config.levels[1].trigger_description
        child_trigger = {
            'triggerid': '100',
            'description': self.trigger_config.levels[0].trigger_description,
            'dependencies': [{'triggerid': '200', 'description': parent_description}],
        }
        parent_trigger = {'triggerid': '200', 'description': parent_description, 'dependencies': []}
        mock_get_trigger.side_effect = [child_trigger, parent_trigger]
        prepared = {
            'child': child,
            'child_level': self.trigger_config.levels[0],
            'child_assignment': assignment,
            'parents_on_server': [(parent, parent_assignment)],
        }
        api = MagicMock()

        result = _sync_prepared_child_dependency(prepared, api, trigger_config=self.trigger_config)

        self.assertEqual(result, {'child': str(child), 'parent': str(parent), 'server': str(server), 'changed': False})
        api.trigger.update.assert_not_called()


class FakeInterfaceManager:
    def __init__(self, interfaces):
        self.interfaces = interfaces

    def select_related(self, *fields):
        self.selected_fields = fields
        return self

    def order_by(self, *fields):
        self.ordered_fields = fields
        return self.interfaces
