from unittest.mock import MagicMock, patch

from django.test import TestCase

from nbxsync.choices import ZabbixProxyTypeChoices, ZabbixTLSChoices
from nbxsync.models import ZabbixProxy, ZabbixProxyGroup, ZabbixServer
from nbxsync.utils.sync.proxysync import ProxySync


class ProxySyncIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.zabbixserver = ZabbixServer.objects.create(
            name='Zabbix Server A',
            description='Test Server',
            url='http://example.com',
            token='dummy-token',
            validate_certs=True,
        )

        cls.proxygroup = ZabbixProxyGroup.objects.create(name='Proxy Group A', zabbixserver=cls.zabbixserver, proxy_groupid=456)

        cls.zabbix_proxy = ZabbixProxy.objects.create(
            name='Active Proxy #1',
            zabbixserver=cls.zabbixserver,
            proxygroup=cls.proxygroup,
            operating_mode=ZabbixProxyTypeChoices.ACTIVE,
            local_address='192.168.1.1',
            local_port=10051,
            allowed_addresses=['10.0.0.1'],
            tls_accept=[ZabbixTLSChoices.PSK],
            tls_psk_identity='psk-id',
            tls_psk='2AB09AD2496109A3BFAC0C6BB4D37CEF',
        )

    def test_get_create_params_active_proxy(self):
        sync = ProxySync(api=MagicMock(), netbox_obj=self.zabbix_proxy)
        params = sync.get_create_params()

        self.assertEqual(params['name'], 'Active Proxy #1')
        self.assertEqual(params['local_address'], '192.168.1.1')
        self.assertEqual(params['allowed_addresses'], '10.0.0.1')
        self.assertEqual(params['proxy_groupid'], 456)
        self.assertEqual(params['tls_accept'], 2)  # 2 = ZabbixTLSChoices.PSK
        self.assertEqual(params['tls_psk_identity'], 'psk-id')

    def test_get_update_params_includes_proxyid(self):
        self.zabbix_proxy.proxyid = '123'
        sync = ProxySync(api=MagicMock(), netbox_obj=self.zabbix_proxy)
        params = sync.get_update_params()
        self.assertEqual(params['proxyid'], '123')

    @patch('nbxsync.utils.sync.proxysync.ZabbixProxyGroup.objects.get')
    def test_sync_from_zabbix_sets_fields(self, mock_get_group):
        self.zabbix_proxy.save = MagicMock()
        self.zabbix_proxy.update_sync_info = MagicMock()

        group = self.proxygroup
        mock_get_group.return_value = group

        data = {
            'proxyid': '200',
            'name': 'Synced Proxy',
            'description': 'Updated Desc',
            'operating_mode': ZabbixProxyTypeChoices.ACTIVE,
            'tls_accept': 6,
            'tls_psk_identity': 'updated-id',
            'tls_subject': 'CN=test',
            'tls_issuer': 'issuer',
            'custom_timeouts': '0',
            'proxy_groupid': group.proxy_groupid,
            'local_address': '192.168.1.2',
            'local_port': '10052',
            'allowed_addresses': '192.168.1.5, 192.168.1.6',
        }

        sync = ProxySync(api=MagicMock(), netbox_obj=self.zabbix_proxy)
        sync.sync_from_zabbix(data)

        self.assertEqual(self.zabbix_proxy.proxyid, '200')
        self.assertEqual(self.zabbix_proxy.name, 'Synced Proxy')
        self.assertEqual(self.zabbix_proxy.tls_psk_identity, 'updated-id')
        self.assertEqual(self.zabbix_proxy.tls_accept, [1])
        self.assertEqual(self.zabbix_proxy.allowed_addresses, ['192.168.1.5', '192.168.1.6'])

        self.zabbix_proxy.save.assert_called_once()
        self.zabbix_proxy.update_sync_info.assert_called_once_with(success=True, message='')

    @patch('nbxsync.utils.sync.proxysync.ZabbixProxyGroup.objects.get', side_effect=ZabbixProxyGroup.DoesNotExist)
    def test_sync_from_zabbix_handles_missing_group(self, mock_get_group):
        data = {
            'proxyid': '200',
            'proxy_groupid': 9999,  # Non-existent group
            'operating_mode': ZabbixProxyTypeChoices.ACTIVE,
            'local_address': '192.168.5.5',
            'local_port': '10051',
            'allowed_addresses': '10.0.0.5',
            'tls_accept': 1,
        }
        sync = ProxySync(api=MagicMock(), netbox_obj=self.zabbix_proxy)
        sync.sync_from_zabbix(data)

        # Should safely handle missing group
        self.assertIsNone(self.zabbix_proxy.proxygroup)

    def test_api_object_and_result_key_methods(self):
        mock_api = MagicMock()
        sync = ProxySync(api=mock_api, netbox_obj=self.zabbix_proxy)

        # Trigger the methods
        result = sync.api_object()
        key = sync.result_key()

        # Assert correct access
        self.assertEqual(result, mock_api.proxy)
        self.assertEqual(key, 'proxyids')

    def test_get_create_params_includes_tls_cert_fields(self):
        # Create a proxy with CERT in tls_accept
        proxy = ZabbixProxy.objects.create(
            name='Cert Proxy',
            zabbixserver=self.zabbixserver,
            proxygroup=self.proxygroup,
            operating_mode=ZabbixProxyTypeChoices.ACTIVE,
            local_address='192.168.2.1',
            local_port=10051,
            allowed_addresses=['10.1.1.1'],
            tls_accept=[ZabbixTLSChoices.CERT],
            tls_issuer='ExampleIssuer',
            tls_subject='CN=CertProxy',
        )

        sync = ProxySync(api=MagicMock(), netbox_obj=proxy)
        params = sync.get_create_params()

        self.assertEqual(params['tls_issuer'], 'ExampleIssuer')
        self.assertEqual(params['tls_subject'], 'CN=CertProxy')
        self.assertIn('tls_accept', params)
        self.assertTrue(params['tls_accept'] & ZabbixTLSChoices.CERT)

    def test_get_create_params_passive_no_tls(self):
        proxy = ZabbixProxy.objects.create(
            name='Passive Proxy No TLS',
            zabbixserver=self.zabbixserver,
            operating_mode=ZabbixProxyTypeChoices.PASSIVE,
            address='10.10.10.10',
            port=10051,
            tls_connect=ZabbixTLSChoices.NO_ENCRYPTION,
        )
        sync = ProxySync(api=MagicMock(), netbox_obj=proxy)
        params = sync.get_create_params()

        self.assertEqual(params['address'], '10.10.10.10')
        self.assertEqual(params['port'], '10051')
        self.assertEqual(params['tls_connect'], ZabbixTLSChoices.NO_ENCRYPTION)
        self.assertNotIn('tls_psk', params)
        self.assertNotIn('tls_issuer', params)

    def test_get_create_params_passive_with_psk(self):
        proxy = ZabbixProxy.objects.create(
            name='Passive Proxy PSK',
            zabbixserver=self.zabbixserver,
            operating_mode=ZabbixProxyTypeChoices.PASSIVE,
            address='10.10.10.11',
            port=10052,
            tls_connect=ZabbixTLSChoices.PSK,
            tls_psk_identity='psk-identity',
            tls_psk='ED9A6CF659308CE2D0CFBA26572696AD',
        )
        sync = ProxySync(api=MagicMock(), netbox_obj=proxy)
        params = sync.get_create_params()

        self.assertEqual(params['tls_connect'], ZabbixTLSChoices.PSK)
        self.assertEqual(params['tls_psk_identity'], 'psk-identity')
        self.assertEqual(params['tls_psk'], 'ED9A6CF659308CE2D0CFBA26572696AD')

    def test_get_create_params_passive_with_cert(self):
        proxy = ZabbixProxy.objects.create(
            name='Passive Proxy CERT',
            zabbixserver=self.zabbixserver,
            operating_mode=ZabbixProxyTypeChoices.PASSIVE,
            address='10.10.10.12',
            port=10053,
            tls_connect=ZabbixTLSChoices.CERT,
            tls_issuer='ExampleIssuer',
            tls_subject='CN=PassiveCert',
        )
        sync = ProxySync(api=MagicMock(), netbox_obj=proxy)
        params = sync.get_create_params()

        self.assertEqual(params['tls_connect'], ZabbixTLSChoices.CERT)
        self.assertEqual(params['tls_issuer'], 'ExampleIssuer')
        self.assertEqual(params['tls_subject'], 'CN=PassiveCert')

    def test_get_create_params_passive_no_tls_with_custom_timeouts(self):
        proxy = ZabbixProxy.objects.create(
            name='Passive Proxy No TLS',
            zabbixserver=self.zabbixserver,
            operating_mode=ZabbixProxyTypeChoices.PASSIVE,
            address='10.10.10.10',
            port=10051,
            tls_connect=ZabbixTLSChoices.NO_ENCRYPTION,
            custom_timeouts=1,
            timeout_zabbix_agent='1m',
            timeout_simple_check='1m',
            timeout_snmp_agent='1m',
            timeout_external_check='1m',
            timeout_db_monitor='1m',
            timeout_http_agent='1m',
            timeout_ssh_agent='1m',
            timeout_telnet_agent='1m',
            timeout_script='1m',
            timeout_browser='1m',
        )
        sync = ProxySync(api=MagicMock(), netbox_obj=proxy)
        params = sync.get_create_params()

        self.assertEqual(params['address'], '10.10.10.10')
        self.assertEqual(params['port'], '10051')
        self.assertEqual(params['tls_connect'], ZabbixTLSChoices.NO_ENCRYPTION)
        self.assertEqual(params['custom_timeouts'], 1)
        self.assertEqual(params['timeout_zabbix_agent'], '1m')
        self.assertNotIn('tls_psk', params)
        self.assertNotIn('tls_issuer', params)

    @patch('nbxsync.utils.sync.proxysync.ZabbixProxyGroup.objects.get')
    def test_sync_from_zabbix_unsets_proxygroup_when_id_is_zero(self, mock_get_group):
        self.zabbix_proxy.proxygroup = self.proxygroup  # initially set
        self.zabbix_proxy.save = MagicMock()
        self.zabbix_proxy.update_sync_info = MagicMock()

        data = {
            'proxyid': '201',
            'proxy_groupid': 0,  # triggers unset
            'tls_accept': 1,
            'operating_mode': ZabbixProxyTypeChoices.ACTIVE,
            'local_address': '192.168.1.3',
            'local_port': '10051',
            'allowed_addresses': '10.0.0.3',
        }

        sync = ProxySync(api=MagicMock(), netbox_obj=self.zabbix_proxy)
        sync.sync_from_zabbix(data)

        self.assertIsNone(self.zabbix_proxy.proxygroup)
        self.zabbix_proxy.save.assert_called_once()
        self.zabbix_proxy.update_sync_info.assert_called_once_with(success=True, message='')

    @patch('nbxsync.utils.sync.proxysync.ZabbixProxyGroup.objects.get', side_effect=ZabbixProxyGroup.DoesNotExist)
    def test_sync_from_zabbix_handles_save_exception(self, mock_get_group):
        # Cause validation error by setting group to None (active proxies require local_address)
        self.zabbix_proxy.proxygroup = None
        self.zabbix_proxy.local_address = None
        self.zabbix_proxy.update_sync_info = MagicMock()

        data = {
            'proxyid': '202',
            'proxy_groupid': 9999,
            'operating_mode': ZabbixProxyTypeChoices.ACTIVE,
            'tls_accept': 1,
            'local_address': None,  # Will trigger validation error
            'local_port': '10051',
            'allowed_addresses': '',
        }

        sync = ProxySync(api=MagicMock(), netbox_obj=self.zabbix_proxy)
        sync.sync_from_zabbix(data)

        self.zabbix_proxy.update_sync_info.assert_called_once()
        args, kwargs = self.zabbix_proxy.update_sync_info.call_args
        self.assertFalse(kwargs['success'])
        self.assertIn('local_address', kwargs['message'])  # ValidationError text

    def test_decode_bitmask_single_flag(self):
        sync = ProxySync(api=MagicMock(), netbox_obj=self.zabbix_proxy)
        self.assertEqual(sync.decode_bitmask(1), [1])

    def test_decode_bitmask_multiple_flags(self):
        sync = ProxySync(api=MagicMock(), netbox_obj=self.zabbix_proxy)
        self.assertEqual(sync.decode_bitmask(3), [1, 2])

    def test_decode_bitmask_all_flags(self):
        sync = ProxySync(api=MagicMock(), netbox_obj=self.zabbix_proxy)
        self.assertEqual(sync.decode_bitmask(7), [1, 2, 4])

    def test_decode_bitmask_none(self):
        sync = ProxySync(api=MagicMock(), netbox_obj=self.zabbix_proxy)
        self.assertEqual(sync.decode_bitmask(0), [])

    def test_decode_bitmask_custom_flags(self):
        sync = ProxySync(api=MagicMock(), netbox_obj=self.zabbix_proxy)
        self.assertEqual(sync.decode_bitmask(10, flags=(2, 8)), [2, 8])
