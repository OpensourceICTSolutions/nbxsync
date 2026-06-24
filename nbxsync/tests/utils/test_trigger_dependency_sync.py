from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from nbxsync.settings import PluginSettingsModel
from nbxsync.utils.trigger_dependency_sync import build_dependency_payload, get_dependency_level, normalized_role_tokens, sync_device_trigger_dependencies


class TriggerDependencySyncTestCase(TestCase):
    def setUp(self):
        self.trigger_config = PluginSettingsModel().trigger_dependencies

    def test_normalized_role_tokens_reads_name_and_slug(self):
        device = SimpleNamespace(role=SimpleNamespace(name='Meraki MX', slug='meraki-mx'))

        self.assertEqual(normalized_role_tokens(device), {'meraki mx', 'meraki-mx'})

    def test_role_matching_uses_configured_level_tokens(self):
        access_point = SimpleNamespace(role=SimpleNamespace(name='Access Point', slug='access-point'))
        switch = SimpleNamespace(role=SimpleNamespace(name='Switch', slug='switch'))
        gateway = SimpleNamespace(role=SimpleNamespace(name='Security Appliance', slug='security-appliance'))
        firewall = SimpleNamespace(role=SimpleNamespace(name='Firewall', slug='firewall'))

        access_point_index, access_point_level = get_dependency_level(access_point, trigger_config=self.trigger_config)
        switch_index, switch_level = get_dependency_level(switch, trigger_config=self.trigger_config)
        gateway_index, gateway_level = get_dependency_level(gateway, trigger_config=self.trigger_config)
        firewall_index, firewall_level = get_dependency_level(firewall, trigger_config=self.trigger_config)

        self.assertEqual((access_point_index, access_point_level.name), (0, 'access_point'))
        self.assertEqual((switch_index, switch_level.name), (1, 'switch'))
        self.assertEqual((gateway_index, gateway_level.name), (2, 'gateway'))
        self.assertEqual((firewall_index, firewall_level.name), (2, 'gateway'))

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

    @patch('nbxsync.utils.trigger_dependency_sync.get_child_devices', return_value=[])
    @patch('nbxsync.utils.trigger_dependency_sync._sync_child_dependency', return_value={'child': 'ap', 'changed': True})
    @patch('nbxsync.utils.trigger_dependency_sync.get_plugin_settings')
    def test_sync_device_trigger_dependencies_syncs_lowest_level_device(self, mock_settings, mock_sync_child, _mock_get_children):
        self.trigger_config.enabled = True
        mock_settings.return_value = SimpleNamespace(trigger_dependencies=self.trigger_config)
        access_point = SimpleNamespace(
            role=SimpleNamespace(name='Access Point', slug='access-point'),
            _meta=SimpleNamespace(model_name='device'),
        )

        result = sync_device_trigger_dependencies(access_point)

        self.assertEqual(result, [{'child': 'ap', 'changed': True}])
        mock_sync_child.assert_called_once_with(access_point, trigger_config=self.trigger_config)
