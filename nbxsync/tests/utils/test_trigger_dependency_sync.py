from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import TestCase

from nbxsync.settings import PluginSettingsModel
from nbxsync.utils.trigger_dependency_sync import build_dependency_payload, get_connected_devices, get_dependency_level, normalized_role_tokens, sync_device_trigger_dependencies


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

        payload = build_dependency_payload(
            child_trigger,
            ['300'],
            {self.trigger_config.levels[1].trigger_description},
        )

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
        access_point = SimpleNamespace(
            role=SimpleNamespace(name='Access Point', slug='access-point'),
            _meta=SimpleNamespace(model_name='device'),
        )

        result = sync_device_trigger_dependencies(access_point)

        self.assertEqual(result, [{'child': 'ap', 'changed': True}])
        mock_sync_children.assert_called_once_with([access_point], trigger_config=self.trigger_config)

    @patch('nbxsync.utils.trigger_dependency_sync.ZabbixConnection')
    @patch('nbxsync.utils.trigger_dependency_sync.get_host_assignment')
    @patch('nbxsync.utils.trigger_dependency_sync.get_parent_devices')
    @patch('nbxsync.utils.trigger_dependency_sync.get_child_devices')
    @patch('nbxsync.utils.trigger_dependency_sync.get_plugin_settings')
    def test_sync_device_trigger_dependencies_reuses_connection_per_zabbix_server(
        self,
        mock_settings,
        mock_get_children,
        mock_get_parents,
        mock_get_assignment,
        mock_connection,
    ):
        self.trigger_config.enabled = True
        mock_settings.return_value = SimpleNamespace(trigger_dependencies=self.trigger_config)
        zabbixserver = SimpleNamespace(name='Zabbix 1')
        gateway = SimpleNamespace(
            role=SimpleNamespace(name='Gateway', slug='gateway'),
            _meta=SimpleNamespace(model_name='device'),
        )
        child_1 = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))
        child_2 = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))
        child_1_assignment = SimpleNamespace(hostid='101', zabbixserver_id=1, zabbixserver=zabbixserver)
        child_2_assignment = SimpleNamespace(hostid='102', zabbixserver_id=1, zabbixserver=zabbixserver)
        parent_assignment = SimpleNamespace(hostid='201', zabbixserver_id=1, zabbixserver=zabbixserver)
        api = MagicMock()
        mock_connection.return_value.__enter__.return_value = api
        mock_get_children.return_value = [child_1, child_2]
        mock_get_parents.return_value = [gateway]

        def assignment_for(device):
            if device is child_1:
                return child_1_assignment
            if device is child_2:
                return child_2_assignment
            if device is gateway:
                return parent_assignment

        def trigger_for(_api, hostid, description):
            if description == 'AP status':
                return {'triggerid': f'child-{hostid}', 'description': description, 'dependencies': []}
            return {'triggerid': f'parent-{hostid}', 'description': description, 'dependencies': []}

        mock_get_assignment.side_effect = assignment_for

        with patch('nbxsync.utils.trigger_dependency_sync.get_host_trigger', side_effect=trigger_for):
            result = sync_device_trigger_dependencies(gateway)

        mock_connection.assert_called_once_with(zabbixserver)
        self.assertEqual(api.trigger.update.call_count, 2)
        self.assertEqual(
            result,
            [
                {'child': str(child_1), 'parent': str(gateway), 'changed': True},
                {'child': str(child_2), 'parent': str(gateway), 'changed': True},
            ],
        )


class FakeInterfaceManager:
    def __init__(self, interfaces):
        self.interfaces = interfaces

    def select_related(self, *fields):
        self.selected_fields = fields
        return self

    def order_by(self, *fields):
        self.ordered_fields = fields
        return self.interfaces
