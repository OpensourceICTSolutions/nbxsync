from django.core.exceptions import ValidationError
from django.test import TestCase

from nbxsync.choices import ZabbixProxyTypeChoices, ZabbixTLSChoices
from nbxsync.models import ZabbixProxy, ZabbixServer, ZabbixProxyGroup


class ZabbixProxyTestCase(TestCase):
    def setUp(self):
        self.zabbixserver = ZabbixServer.objects.create(name='Zabbix Server', url='http://127.0.0.1', token='superSecretToken')

    def test_valid_active_proxy(self):
        proxy = ZabbixProxy(name='Active Proxy', zabbixserver=self.zabbixserver, local_address='192.168.1.1', operating_mode=ZabbixProxyTypeChoices.ACTIVE)

        proxy.full_clean()
        proxy.save()
        self.assertEqual(proxy.address, '')
        self.assertEqual(proxy.port, '')
        self.assertEqual(proxy.tls_connect, ZabbixTLSChoices.NO_ENCRYPTION)

    def test_valid_passive_proxy(self):
        proxy = ZabbixProxy(name='Passive Proxy', zabbixserver=self.zabbixserver, address='10.0.0.1', operating_mode=ZabbixProxyTypeChoices.PASSIVE)
        proxy.full_clean()
        proxy.save()

        self.assertEqual(proxy.local_address, '')
        self.assertEqual(proxy.local_port, 10051)
        self.assertEqual(proxy.allowed_addresses, [])
        self.assertEqual(proxy.tls_accept, [ZabbixTLSChoices.NO_ENCRYPTION])

    def test_invalid_allowed_address(self):
        proxy = ZabbixProxy(name='Invalid IP', zabbixserver=self.zabbixserver, local_address='192.168.0.1', operating_mode=ZabbixProxyTypeChoices.ACTIVE, allowed_addresses=['not-an-ip'])

        with self.assertRaises(ValidationError) as cm:
            proxy.full_clean()

        self.assertIn('allowed_addresses', cm.exception.message_dict)

    def test_duplicate_allowed_addresses(self):
        proxy = ZabbixProxy(name='Dup IPs', zabbixserver=self.zabbixserver, local_address='192.168.0.1', operating_mode=ZabbixProxyTypeChoices.ACTIVE, allowed_addresses=['10.0.0.1', '10.0.0.1'])

        with self.assertRaises(ValidationError) as cm:
            proxy.full_clean()

        self.assertIn('allowed_addresses', cm.exception.message_dict)

    def test_tls_psk_validation(self):
        proxy = ZabbixProxy(name='PSK Test', zabbixserver=self.zabbixserver, address='10.0.0.2', operating_mode=ZabbixProxyTypeChoices.PASSIVE, tls_connect=ZabbixTLSChoices.PSK, tls_psk='abc123', tls_psk_identity='')

        with self.assertRaises(ValidationError) as cm:
            proxy.full_clean()

        self.assertIn('TLS PSK must be at least 32 characters long', str(cm.exception))
        self.assertIn('TLS PSK Identity must be provided when using PSK encryption', str(cm.exception))

    def test_custom_timeout_invalid_format(self):
        proxy = ZabbixProxy(name='Bad Timeout', zabbixserver=self.zabbixserver, local_address='192.168.1.1', operating_mode=ZabbixProxyTypeChoices.ACTIVE, custom_timeouts=True, timeout_zabbix_agent='bad')

        with self.assertRaises(ValidationError) as cm:
            proxy.full_clean()

        self.assertIn('timeout_zabbix_agent', cm.exception.message_dict)

    def test_invalid_local_address_format(self):
        proxy = ZabbixProxy(name='Bad Local', zabbixserver=self.zabbixserver, local_address='not@@valid', operating_mode=ZabbixProxyTypeChoices.ACTIVE)

        with self.assertRaises(ValidationError) as cm:
            proxy.full_clean()

        self.assertIn('not@@valid', cm.exception.message_dict['local_address'][0])
        self.assertIn('neither a valid domain name nor an IP address', cm.exception.message_dict['local_address'][0])

    def test_missing_address_for_passive_raises(self):
        proxy = ZabbixProxy(name='Missing Passive Address', zabbixserver=self.zabbixserver, address=None, operating_mode=ZabbixProxyTypeChoices.PASSIVE)

        with self.assertRaises(ValidationError) as cm:
            proxy.full_clean()

        self.assertIn('address', cm.exception.message_dict)
        self.assertIn('Address must be specified when Operating Mode is set to Passive', str(cm.exception.message_dict['address']))

    def test_invalid_address_for_passive_proxy(self):
        proxy = ZabbixProxy(name='Invalid Passive Address', zabbixserver=self.zabbixserver, address='invalid@@', operating_mode=ZabbixProxyTypeChoices.PASSIVE)

        with self.assertRaises(ValidationError) as cm:
            proxy.full_clean()

        self.assertIn('invalid@@', cm.exception.message_dict['address'][0])
        self.assertIn('neither a valid domain name nor an IP address', cm.exception.message_dict['address'][0])

    def test_tls_psk_invalid_format(self):
        proxy = ZabbixProxy(name='PSK Format', zabbixserver=self.zabbixserver, address='10.0.0.2', operating_mode=ZabbixProxyTypeChoices.PASSIVE, tls_connect=ZabbixTLSChoices.PSK, tls_psk='!' * 32, tls_psk_identity='identity123')

        with self.assertRaises(ValidationError) as cm:
            proxy.full_clean()

        self.assertIn('tls_psk', cm.exception.message_dict)
        self.assertIn('TLS PSK must contain only hexadecimal characters', cm.exception.message_dict['tls_psk'][0])

    def test_custom_timeout_not_a_string(self):
        proxy = ZabbixProxy(name='Non-string Timeout', zabbixserver=self.zabbixserver, local_address='192.168.1.1', operating_mode=ZabbixProxyTypeChoices.ACTIVE, custom_timeouts=True, timeout_zabbix_agent=[30])

        with self.assertRaises(ValidationError) as cm:
            proxy.full_clean()

        self.assertIn('timeout_zabbix_agent', cm.exception.message_dict)
        self.assertIn("Invalid format: use integer + 's' or 'm', e.g. '90s', '5m'.", cm.exception.message_dict['timeout_zabbix_agent'][0])

    def test_custom_timeout_too_low(self):
        proxy = ZabbixProxy(name='TooShortTimeout', zabbixserver=self.zabbixserver, local_address='192.168.1.1', operating_mode=ZabbixProxyTypeChoices.ACTIVE, custom_timeouts=True, timeout_zabbix_agent='0s')

        with self.assertRaises(ValidationError) as cm:
            proxy.full_clean()

        self.assertIn('Value must be between 1s and 10m.', cm.exception.message_dict['timeout_zabbix_agent'][0])

    def test_custom_timeout_too_high(self):
        proxy = ZabbixProxy(name='TooLongTimeout', zabbixserver=self.zabbixserver, local_address='192.168.1.1', operating_mode=ZabbixProxyTypeChoices.ACTIVE, custom_timeouts=True, timeout_zabbix_agent='11m')

        with self.assertRaises(ValidationError) as cm:
            proxy.full_clean()

        self.assertIn('Value must be between 1s and 10m.', cm.exception.message_dict['timeout_zabbix_agent'][0])

    def test_save_clears_tls_fields_based_on_tls_connect(self):
        proxy = ZabbixProxy(name='TLS Cleanup Test - PSK', zabbixserver=self.zabbixserver, address='10.0.0.2', operating_mode=ZabbixProxyTypeChoices.PASSIVE, tls_connect=ZabbixTLSChoices.PSK, tls_psk='a' * 32, tls_psk_identity='identity123', tls_issuer='IssuerXYZ', tls_subject='SubjectXYZ')
        proxy.full_clean()
        proxy.save()

        self.assertEqual(proxy.tls_issuer, '')
        self.assertEqual(proxy.tls_subject, '')
        self.assertNotEqual(proxy.tls_psk, '')
        self.assertNotEqual(proxy.tls_psk_identity, '')

        # Now test CERT path
        proxy = ZabbixProxy(name='TLS Cleanup Test - CERT', zabbixserver=self.zabbixserver, address='10.0.0.3', operating_mode=ZabbixProxyTypeChoices.PASSIVE, tls_connect=ZabbixTLSChoices.CERT, tls_issuer='IssuerXYZ', tls_subject='SubjectXYZ', tls_psk='a' * 32, tls_psk_identity='identity123')
        proxy.full_clean()
        proxy.save()

        self.assertEqual(proxy.tls_psk_identity, '')
        self.assertEqual(proxy.tls_psk, '')
        self.assertNotEqual(proxy.tls_issuer, '')
        self.assertNotEqual(proxy.tls_subject, '')

    def test_get_tls_accept_display(self):
        proxy = ZabbixProxy.objects.create(name='TLS Display', zabbixserver=self.zabbixserver, local_address='192.168.1.10', operating_mode=ZabbixProxyTypeChoices.ACTIVE, tls_accept=[ZabbixTLSChoices.NO_ENCRYPTION, ZabbixTLSChoices.CERT])
        display = proxy.get_tls_accept_display()

        self.assertIn('No Encryption', display)
        self.assertIn('Certificate', display)
        self.assertEqual(len(display), 2)

    def test_str_representation(self):
        proxy = ZabbixProxy.objects.create(name='ProxyStrTest', zabbixserver=self.zabbixserver, local_address='192.168.1.100', operating_mode=ZabbixProxyTypeChoices.ACTIVE)

        self.assertEqual(str(proxy), 'ProxyStrTest (Active)')

    def test_active_with_group_requires_local_address(self):
        group = ZabbixProxyGroup.objects.create(zabbixserver=self.zabbixserver, name='Group 1', failover_delay=30, min_online=2)
        proxy = ZabbixProxy(name='Active No Local', zabbixserver=self.zabbixserver, proxygroup=group, local_address='', operating_mode=ZabbixProxyTypeChoices.ACTIVE)

        with self.assertRaises(ValidationError) as cm:
            proxy.full_clean()

        self.assertIn('local_address', cm.exception.message_dict)
        self.assertIn('Local Address must be specified when part of a ProxyGroup and Operating Mode is set to Active', cm.exception.message_dict['local_address'][0])
