from unittest.mock import MagicMock

from django.test import TestCase

from nbxsync.models import ZabbixProxyGroup, ZabbixServer
from nbxsync.utils.sync.proxygroupsync import ProxyGroupSync


class ProxyGroupSyncIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.zabbixserver = ZabbixServer.objects.create(name='Zabbix Server A', description='Test Server', url='http://example.com', token='dummy-token', validate_certs=True)
        cls.proxygroup = ZabbixProxyGroup.objects.create(name='Group A', zabbixserver=cls.zabbixserver, proxy_groupid=456, description='Failover Group A', failover_delay='1m', min_online=2)

    def test_get_create_params(self):
        sync = ProxyGroupSync(api=MagicMock(), netbox_obj=self.proxygroup)
        params = sync.get_create_params()

        self.assertEqual(params['name'], 'Group A')
        self.assertEqual(params['description'], 'Failover Group A')
        self.assertEqual(params['failover_delay'], '1m')
        self.assertEqual(params['min_online'], 2)

    def test_get_update_params(self):
        sync = ProxyGroupSync(api=MagicMock(), netbox_obj=self.proxygroup)
        params = sync.get_update_params()

        self.assertEqual(params['proxy_groupid'], 456)
        self.assertEqual(params['name'], 'Group A')
        self.assertEqual(params['failover_delay'], '1m')
        self.assertEqual(params['min_online'], 2)

    def test_api_object_and_result_key(self):
        mock_api = MagicMock()
        sync = ProxyGroupSync(api=mock_api, netbox_obj=self.proxygroup)

        self.assertEqual(sync.api_object(), mock_api.proxygroup)
        self.assertEqual(sync.result_key(), 'proxy_groupids')

    def test_sync_from_zabbix_sets_fields(self):
        self.proxygroup.save = MagicMock()
        self.proxygroup.update_sync_info = MagicMock()

        data = {
            'proxy_groupid': 789,
            'name': 'Updated Group',
            'description': 'Updated description',
            'failover_delay': '2m',
            'min_online': 5,
        }

        sync = ProxyGroupSync(api=MagicMock(), netbox_obj=self.proxygroup)
        sync.sync_from_zabbix(data)

        self.assertEqual(self.proxygroup.proxy_groupid, 789)
        self.assertEqual(self.proxygroup.name, 'Updated Group')
        self.assertEqual(self.proxygroup.description, 'Updated description')
        self.assertEqual(self.proxygroup.failover_delay, '2m')
        self.assertEqual(self.proxygroup.min_online, 5)

        self.proxygroup.save.assert_called_once()
        self.proxygroup.update_sync_info.assert_called_once_with(success=True, message='')

    def test_sync_from_zabbix_handles_save_exception(self):
        # Make .save() raise an error
        def failing_save():
            raise ValueError('Save failed')

        self.proxygroup.save = failing_save
        self.proxygroup.update_sync_info = MagicMock()

        data = {'proxy_groupid': 888, 'name': 'Bad Save Group'}

        sync = ProxyGroupSync(api=MagicMock(), netbox_obj=self.proxygroup)

        # Patch sync to handle the exception like ProxySync does
        try:
            sync.sync_from_zabbix(data)
        except Exception:
            pass  # Expect failure here

        self.proxygroup.update_sync_info.assert_called_once()
        args, kwargs = self.proxygroup.update_sync_info.call_args
        self.assertFalse(kwargs['success'])
        self.assertIn('Save failed', kwargs['message'])
