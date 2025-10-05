from unittest import TestCase
from unittest.mock import MagicMock, patch

from nbxsync.choices import HostInterfaceRequirementChoices
from nbxsync.jobs.synctemplates import SyncTemplatesJob


class SyncTemplatesJobTestCase(TestCase):
    def setUp(self):
        self.mock_instance = MagicMock()
        self.mock_instance.id = 1

        # Minimal realistic mock from call1.json
        self.template_data = [
            {
                'templateid': '10001',
                'name': 'Test Template',
                'macros': [{'macro': '{$ENV}', 'value': 'prod'}],
            }
        ]

        # Minimal mock for item.get
        self.item_data = [
            {
                'itemid': '20001',
                'name': 'CPU Usage',
                'type': '1',  # AGENT
            }
        ]

        # Minimal mock for discoveryrule.get
        self.discovery_rule_data = [
            {
                'itemid': '30001',
                'items': [
                    {'itemid': '30002', 'type': '2'}  # SNMP
                ],
                'graphs': [],
                'hostPrototypes': [],
                'filter': {},
            }
        ]

    @patch('nbxsync.jobs.synctemplates.create_or_update_zabbixmacro')
    @patch('nbxsync.jobs.synctemplates.create_or_update_zabbixtemplate')
    @patch('nbxsync.jobs.synctemplates.ZabbixConnection')
    def test_run_successful_sync(self, mock_connection, mock_template, mock_macro):
        mock_api = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_api

        # Simulate API responses
        mock_api.template.get.return_value = [
            {
                'templateid': '10001',
                'name': 'Test Template',
                'macros': [{'macro': '{$FOO}', 'value': 'bar'}],
            }
        ]
        mock_api.item.get.return_value = [{'type': '20'}]  # SNMP agent
        mock_api.discoveryrule.get.return_value = [{'items': [{'type': '0'}]}]  # Zabbix agent

        class MockTemplate:
            def __init__(self):
                self._interface_requirements = []
                self.save = MagicMock()

            @property
            def interface_requirements(self):
                return self._interface_requirements

            @interface_requirements.setter
            def interface_requirements(self, value):
                self._interface_requirements = value

        template_obj = MockTemplate()
        mock_template.return_value = template_obj

        job = SyncTemplatesJob(instance=self.mock_instance)
        job.run()

        # Assert correct API calls
        mock_api.template.get.assert_called_once_with(output='extend', selectMacros='extend')
        mock_macro.assert_called_once_with(macro={'macro': '{$FOO}', 'value': 'bar'}, zabbixtemplate=template_obj)

        mock_template.assert_called_once_with(
            template={'templateid': '10001', 'name': 'Test Template', 'macros': [{'macro': '{$FOO}', 'value': 'bar'}]},
            zabbixserver=self.mock_instance,
        )
        # Assert result
        expected = {HostInterfaceRequirementChoices.AGENT, HostInterfaceRequirementChoices.SNMP}
        actual = set(template_obj.interface_requirements)
        self.assertEqual(actual, expected)

        template_obj.save.assert_called_once()

    @patch('nbxsync.jobs.synctemplates.ZabbixConnection', side_effect=ConnectionError('Zabbix login failed'))
    def test_login_failure(self, mock_connection):
        job = SyncTemplatesJob(instance=self.mock_instance)
        with self.assertRaises(ConnectionError) as cm:
            job.run()
        self.assertIn('Login error', str(cm.exception))

    @patch('nbxsync.jobs.synctemplates.ZabbixConnection')
    @patch('nbxsync.jobs.synctemplates.create_or_update_zabbixtemplate', side_effect=Exception('Boom'))
    def test_runtime_error(self, mock_template, mock_connection):
        mock_api = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_api

        mock_api.template.get.return_value = self.template_data
        mock_api.item.get.return_value = []
        mock_api.discoveryrule.get.return_value = []

        job = SyncTemplatesJob(instance=self.mock_instance)
        with self.assertRaises(RuntimeError) as cm:
            job.run()
        self.assertIn('Unexpected error', str(cm.exception))

    @patch('nbxsync.jobs.synctemplates.create_or_update_zabbixmacro')
    @patch('nbxsync.jobs.synctemplates.create_or_update_zabbixtemplate')
    @patch('nbxsync.jobs.synctemplates.ZabbixConnection')
    def test_interface_requirement_any(self, mock_connection, mock_template, mock_macro):
        mock_api = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_api

        mock_api.template.get.return_value = [
            {
                'templateid': '10001',
                'name': 'Test Template',
                'macros': [],
            }
        ]
        mock_api.item.get.return_value = [{'type': '10'}]  # type 10 → ANY
        mock_api.discoveryrule.get.return_value = []

        class MockTemplate:
            def __init__(self):
                self.interface_requirements = []
                self.save = MagicMock()

        template_obj = MockTemplate()
        mock_template.return_value = template_obj

        job = SyncTemplatesJob(instance=self.mock_instance)
        job.run()

        self.assertEqual(template_obj.interface_requirements, [HostInterfaceRequirementChoices.ANY])
        template_obj.save.assert_called_once()

    @patch('nbxsync.jobs.synctemplates.create_or_update_zabbixmacro')
    @patch('nbxsync.jobs.synctemplates.create_or_update_zabbixtemplate')
    @patch('nbxsync.jobs.synctemplates.ZabbixConnection')
    def test_interface_requirement_none(self, mock_connection, mock_template, mock_macro):
        mock_api = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_api

        mock_api.template.get.return_value = [
            {
                'templateid': '10002',
                'name': 'None Template',
                'macros': [],
            }
        ]
        mock_api.item.get.return_value = [{'type': '2'}]  # type 2 → NONE
        mock_api.discoveryrule.get.return_value = []

        class MockTemplate:
            def __init__(self):
                self.interface_requirements = []
                self.save = MagicMock()

        template_obj = MockTemplate()
        mock_template.return_value = template_obj

        job = SyncTemplatesJob(instance=self.mock_instance)
        job.run()

        self.assertEqual(template_obj.interface_requirements, [HostInterfaceRequirementChoices.NONE])
        template_obj.save.assert_called_once()

    @patch('nbxsync.jobs.synctemplates.create_or_update_zabbixmacro')
    @patch('nbxsync.jobs.synctemplates.create_or_update_zabbixtemplate')
    @patch('nbxsync.jobs.synctemplates.ZabbixConnection')
    def test_skips_uncreated_template(self, mock_connection, mock_template, mock_macro):
        mock_api = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_api

        mock_api.template.get.return_value = [
            {
                'templateid': '10099',
                'name': 'Missing Template',
                'macros': [{'macro': '{$FOO}', 'value': 'bar'}],
            }
        ]
        mock_api.item.get.return_value = []  # no items
        mock_api.discoveryrule.get.return_value = []  # no rules

        mock_template.return_value = None  # simulate failure to create template

        job = SyncTemplatesJob(instance=self.mock_instance)
        job.run()

        mock_macro.assert_not_called()  # No macros should be created
        mock_template.assert_called_once()  # Attempted to create the template

    @patch('nbxsync.jobs.synctemplates.create_or_update_zabbixtemplate')
    @patch('nbxsync.jobs.synctemplates.ZabbixTemplate')
    @patch('nbxsync.jobs.synctemplates.ZabbixConnection')
    def test_deletes_orphan_templates(self, mock_connection, mock_zabbix_template, mock_create_template):
        # Zabbix returns only template 10001
        mock_api = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_api
        mock_api.template.get.return_value = [{'templateid': '10001', 'name': 'Kept Template', 'macros': []}]
        mock_api.item.get.return_value = []
        mock_api.discoveryrule.get.return_value = []

        # First filter().values_list(...) -> existing NetBox templates: 10001 (kept) and 10002 (orphan)
        qs_values = MagicMock()
        qs_values.values_list.return_value = [10001, 10002]

        # Second filter(...).delete() should be called with templateid__in={10002}
        qs_delete = MagicMock()

        # Chain the two different filter calls
        mock_zabbix_template.objects.filter.side_effect = [qs_values, qs_delete]

        # create_or_update_zabbixtemplate returns a stub obj with interface_requirements
        class StubTemplate:
            def __init__(self):
                self.interface_requirements = []

        mock_create_template.return_value = StubTemplate()

        job = SyncTemplatesJob(instance=self.mock_instance)
        job.run()

        # Assert the second filter call was for the orphan id and delete() was invoked
        self.assertEqual(mock_zabbix_template.objects.filter.call_count, 2)
        _, kwargs = mock_zabbix_template.objects.filter.call_args_list[1]
        self.assertEqual(kwargs.get('zabbixserver_id'), self.mock_instance.id)
        self.assertEqual(set(kwargs.get('templateid__in')), {10002})
        qs_delete.delete.assert_called_once()
