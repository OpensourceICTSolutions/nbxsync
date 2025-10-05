from unittest import TestCase
from unittest.mock import MagicMock, patch

from nbxsync.utils import ZabbixConnection


class ZabbixConnectionTests(TestCase):
    def setUp(self):
        self.server = MagicMock()
        self.server.url = 'http://zabbix.example.com'
        self.server.token = 'secret-token'
        self.server.validate_certs = True

    @patch('nbxsync.utils.zabbixconnection.ZabbixAPI')
    def test_successful_connection(self, mock_api_class):
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api

        with ZabbixConnection(self.server) as api:
            mock_api.login.assert_called_once_with(token='secret-token')
            self.assertEqual(api, mock_api)

        mock_api.logout.assert_called_once()

    @patch('nbxsync.utils.zabbixconnection.ZabbixAPI')
    def test_login_failure_raises_connection_error(self, mock_api_class):
        mock_api = MagicMock()
        mock_api.login.side_effect = Exception('Auth failed')
        mock_api_class.return_value = mock_api

        with self.assertRaises(ConnectionError) as cm:
            with ZabbixConnection(self.server):
                pass  # pragma: no cover

        self.assertIn('Failed to login to Zabbix', str(cm.exception))

    @patch('nbxsync.utils.zabbixconnection.ZabbixAPI')
    def test_logout_exception_is_suppressed(self, mock_api_class):
        mock_api = MagicMock()
        mock_api.logout.side_effect = Exception('Logout failed')
        mock_api_class.return_value = mock_api

        # Should not raise anything
        with ZabbixConnection(self.server) as api:
            pass

        mock_api.logout.assert_called_once()
