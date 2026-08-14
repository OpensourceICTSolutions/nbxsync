from unittest.mock import MagicMock, patch

from django.test import TestCase

from pydantic import ValidationError

from nbxsync.choices.syncsot import SyncSOT
from nbxsync.settings import (
    BackgroundSyncConfig,
    PluginSettingsModel,
    SNMPConfig,
    TriggerDependencyConfig,
    TriggerDependencyLevelConfig,
    get_plugin_settings,
)


class PluginSettingsModelTestCase(TestCase):
    def test_default_settings_model(self):
        settings = PluginSettingsModel()
        self.assertEqual(settings.sot.proxygroup, SyncSOT.NETBOX)
        self.assertEqual(settings.sot.hosttemplate, SyncSOT.NETBOX)
        self.assertIsInstance(settings.statusmapping.device, dict)
        self.assertIsInstance(settings.statusmapping.virtualmachine, dict)
        self.assertIsInstance(settings.snmpconfig, SNMPConfig)
        self.assertIsInstance(settings.backgroundsync.objects, BackgroundSyncConfig)
        self.assertIsInstance(settings.backgroundsync.templates, BackgroundSyncConfig)
        self.assertIsInstance(settings.backgroundsync.proxies, BackgroundSyncConfig)
        self.assertIsInstance(settings.backgroundsync.maintenance, BackgroundSyncConfig)
        self.assertIsInstance(settings.trigger_dependencies, TriggerDependencyConfig)
        self.assertFalse(settings.trigger_dependencies.enabled)
        self.assertEqual(settings.trigger_dependencies.levels[1].roles, ['switch', 'sw'])
        self.assertEqual(settings.trigger_dependencies.levels[2].roles, ['gateway', 'gw', 'firewall', 'router'])

    def test_snmp_macro_validation_valid(self):
        config = SNMPConfig(snmp_community='{$VALID_COMM}', snmp_authpass='{$VALID_AUTH}', snmp_privpass='{$VALID_PRIV}')
        self.assertEqual(config.snmp_community, '{$VALID_COMM}')

    def test_snmp_macro_validation_invalid(self):
        with self.assertRaises(ValidationError) as ctx:
            SNMPConfig(snmp_community='INVALID', snmp_authpass='{$VALID}', snmp_privpass='{$VALID}')
        self.assertIn("Value must start with '{$' and end with '}'", str(ctx.exception))

    def test_inheritance_chain_default(self):
        settings = PluginSettingsModel()
        self.assertIn(('role',), settings.inheritance_chain)
        self.assertIn(('device_type', 'manufacturer'), settings.inheritance_chain)
        self.assertIn(('cluster', '_site'), settings.inheritance_chain)
        self.assertNotIn(('cluster', 'site'), settings.inheritance_chain)
        # Hierarchy must not precede role/platform (upgrade-safe precedence)
        self.assertLess(settings.inheritance_chain.index(('role',)), settings.inheritance_chain.index(('site',)))

    @patch('nbxsync.settings.apps')
    def test_get_plugin_settings(self, mock_apps):
        # Create a real PluginSettingsModel instance
        mock_settings = PluginSettingsModel()

        # Mock the return of apps.get_app_config(...).validated_config
        mock_app_config = MagicMock()
        mock_app_config.validated_config = mock_settings
        mock_apps.get_app_config.return_value = mock_app_config

        settings = get_plugin_settings()
        self.assertIsInstance(settings, PluginSettingsModel)

    def test_snmp_macro_validation_invalid_authpass(self):
        with self.assertRaises(ValidationError) as ctx:
            SNMPConfig(
                snmp_community='{$OK}',
                snmp_authpass='NOT_A_MACRO',  # invalid
                snmp_privpass='{$OK}',
            )
        self.assertIn("Value must start with '{$' and end with '}'", str(ctx.exception))

    def test_snmp_macro_validation_invalid_privpass(self):
        with self.assertRaises(ValidationError) as ctx:
            SNMPConfig(
                snmp_community='{$OK}',
                snmp_authpass='{$OK}',
                snmp_privpass='${MALFORMED}',  # invalid suffix/prefix
            )
        self.assertIn("Value must start with '{$' and end with '}'", str(ctx.exception))

    def test_snmp_macro_validation_non_string_values(self):
        # Non-string should also trigger the same validator error (mode='before')
        with self.assertRaises(ValidationError) as ctx:
            SNMPConfig(
                snmp_community=123,  # not a string
                snmp_authpass='{$OK}',
                snmp_privpass='{$OK}',
            )
        self.assertIn("Value must start with '{$' and end with '}'", str(ctx.exception))

    def test_snmp_macro_validation_trailing_brace_missing(self):
        with self.assertRaises(ValidationError) as ctx:
            SNMPConfig(
                snmp_community='{$MISSING_END',  # missing trailing '}'
                snmp_authpass='{$OK}',
                snmp_privpass='{$OK}',
            )
        self.assertIn("Value must start with '{$' and end with '}'", str(ctx.exception))

    def test_trigger_dependency_level_description_validation(self):
        with self.assertRaises(ValidationError) as ctx:
            TriggerDependencyLevelConfig(name='access_point', roles=['ap'], trigger_description=' ')
        self.assertIn('Value must be a non-empty string', str(ctx.exception))

    def test_trigger_dependency_level_role_validation(self):
        with self.assertRaises(ValidationError) as ctx:
            TriggerDependencyLevelConfig(name='access_point', roles=[], trigger_description='AP status')
        self.assertIn('Role tokens must be a non-empty list', str(ctx.exception))

    def test_trigger_dependency_levels_validation(self):
        with self.assertRaises(ValidationError) as ctx:
            TriggerDependencyConfig(levels=[])
        self.assertIn('Dependency levels must be a non-empty list', str(ctx.exception))

    def test_trigger_dependency_level_rejects_blank_role(self):
        with self.assertRaises(ValidationError) as ctx:
            TriggerDependencyLevelConfig(name='switch', roles=['switch', ' '], trigger_description='Switch status')

        self.assertIn('Role tokens must be non-empty strings', str(ctx.exception))

    def test_trigger_dependency_rejects_duplicate_trigger_descriptions(self):
        with self.assertRaises(ValidationError) as ctx:
            TriggerDependencyConfig(
                levels=[
                    TriggerDependencyLevelConfig(name='switch', roles=['switch'], trigger_description='Device status'),
                    TriggerDependencyLevelConfig(name='gateway', roles=['gateway'], trigger_description='Device status'),
                ]
            )

        self.assertIn("Trigger description 'Device status' is used by both", str(ctx.exception))

    def test_trigger_dependency_rejects_overlapping_roles(self):
        with self.assertRaises(ValidationError) as ctx:
            TriggerDependencyConfig(
                levels=[
                    TriggerDependencyLevelConfig(name='switch', roles=['switch'], trigger_description='Switch status'),
                    TriggerDependencyLevelConfig(name='gateway', roles=['gateway', 'SWITCH'], trigger_description='Gateway status'),
                ]
            )

        self.assertIn("Role token 'switch' overlaps between dependency levels", str(ctx.exception))

    def test_trigger_dependency_rejects_normalized_role_overlap(self):
        with self.assertRaises(ValidationError) as ctx:
            TriggerDependencyConfig(
                levels=[
                    TriggerDependencyLevelConfig(name='switch', roles=['core-switch'], trigger_description='Switch status'),
                    TriggerDependencyLevelConfig(name='gateway', roles=['core switch'], trigger_description='Gateway status'),
                ]
            )

        self.assertIn("Role token 'core switch' overlaps between dependency levels", str(ctx.exception))
