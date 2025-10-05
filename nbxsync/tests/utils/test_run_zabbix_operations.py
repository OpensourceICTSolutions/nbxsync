from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from nbxsync.models import ZabbixServer
from nbxsync.utils.sync import run_zabbix_operation


class RunZabbixOperationTests(TestCase):
    def setUp(self):
        self.netbox_obj = MagicMock()
        self.zabbixserver = MagicMock(spec=ZabbixServer)
        self.zabbixserver.id = 123
        self.zabbixserver.url = 'http://mock-zabbix.example.com'
        self.zabbixserver.token = 'mock-token'
        self.zabbixserver.validate_certs = True
        self.sync_class = MagicMock()
        self.operation_result = 'operation completed'

    @patch('nbxsync.utils.sync.run_zabbix_operations.ZabbixConnection')
    @patch('nbxsync.models.ZabbixServer.objects.get')
    def test_successful_operation(self, mock_get, mock_conn):
        self.sync_class.resolve_zabbixserver.return_value = self.zabbixserver
        mock_get.return_value = self.zabbixserver

        mock_api = MagicMock()
        mock_conn.return_value.__enter__.return_value = mock_api

        sync_instance = MagicMock()
        setattr(sync_instance, 'run', Mock(return_value=self.operation_result))
        self.sync_class.return_value = sync_instance

        result = run_zabbix_operation(self.sync_class, self.netbox_obj, 'run')

        self.assertEqual(result, self.operation_result)
        self.sync_class.resolve_zabbixserver.assert_called_once()
        self.sync_class.assert_called_once_with(mock_api, self.netbox_obj)

    def test_resolve_zabbixserver_missing(self):
        del self.sync_class.resolve_zabbixserver

        with self.assertRaises(ValueError):
            run_zabbix_operation(self.sync_class, self.netbox_obj, 'run')

        self.netbox_obj.update_sync_info.assert_called_once()

    @patch('nbxsync.models.ZabbixServer.objects.get')
    def test_zabbixserver_does_not_exist(self, mock_get):
        self.sync_class.resolve_zabbixserver.return_value = self.zabbixserver
        mock_get.side_effect = ZabbixServer.DoesNotExist

        with self.assertRaises(ZabbixServer.DoesNotExist):
            run_zabbix_operation(self.sync_class, self.netbox_obj, 'run')

        self.netbox_obj.update_sync_info.assert_called_once()

    @patch('nbxsync.utils.sync.run_zabbix_operations.ZabbixConnection')
    @patch('nbxsync.models.ZabbixServer.objects.get')
    def test_connection_error(self, mock_get, mock_conn):
        self.sync_class.resolve_zabbixserver.return_value = self.zabbixserver
        mock_get.return_value = self.zabbixserver
        mock_conn.side_effect = ConnectionError('login failed')

        with self.assertRaises(ConnectionError):
            run_zabbix_operation(self.sync_class, self.netbox_obj, 'run')

        self.netbox_obj.update_sync_info.assert_called_once()

    @patch('nbxsync.utils.sync.run_zabbix_operations.ZabbixConnection')
    @patch('nbxsync.models.ZabbixServer.objects.get')
    def test_operation_not_implemented(self, mock_get, mock_conn):
        class DummySync:
            def __init__(self, api, obj, **kwargs):
                pass

            @staticmethod
            def resolve_zabbixserver(obj):
                return self.zabbixserver

        mock_get.return_value = self.zabbixserver
        mock_api = MagicMock()
        mock_conn.return_value.__enter__.return_value = mock_api

        with self.assertRaises(NotImplementedError) as ctx:
            run_zabbix_operation(DummySync, self.netbox_obj, 'not_a_method')

        self.assertIn('DummySync does not implement `not_a_method()`', str(ctx.exception))

        self.netbox_obj.update_sync_info.assert_called_once_with(success=False, message='Unexpected error: DummySync does not implement `not_a_method()`.')
