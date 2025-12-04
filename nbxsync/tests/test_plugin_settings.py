from unittest.mock import MagicMock, patch

from django.test import TestCase
from pydantic import ValidationError

from nbxsync.choices.syncsot import SyncSOT
from nbxsync.settings import PluginSettingsModel, SNMPConfig, BackgroundSyncConfig, get_plugin_settings


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
