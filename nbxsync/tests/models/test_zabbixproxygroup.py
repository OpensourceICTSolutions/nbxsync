from django.core.exceptions import ValidationError
from django.test import TestCase

from nbxsync.models import ZabbixProxyGroup, ZabbixServer


class ZabbixProxyGroupTestCase(TestCase):
    def setUp(self):
        self.zabbixserver = ZabbixServer.objects.create(name='Zabbix Server 1')

    def test_valid_proxy_group(self):
        group = ZabbixProxyGroup.objects.create(zabbixserver=self.zabbixserver, name='Group A', failover_delay='30s', min_online=3)
        self.assertEqual(str(group), 'Group A')

    def test_clean_fails_with_invalid_failover_delay_type(self):
        group = ZabbixProxyGroup(zabbixserver=self.zabbixserver, name='Bad Delay Type', failover_delay=30, min_online=2)

        with self.assertRaises(ValidationError) as cm:
            group.clean()
        self.assertIn('Failover delay must be a string', str(cm.exception))

    def test_clean_fails_with_invalid_failover_delay_format(self):
        group = ZabbixProxyGroup(zabbixserver=self.zabbixserver, name='Bad Format', failover_delay='30x', min_online=2)

        with self.assertRaises(ValidationError) as cm:
            group.clean()
        self.assertIn('Invalid format', str(cm.exception))

    def test_clean_fails_with_failover_delay_below_range(self):
        group = ZabbixProxyGroup(zabbixserver=self.zabbixserver, name='Too Short Delay', failover_delay='5s', min_online=2)

        with self.assertRaises(ValidationError) as cm:
            group.clean()
        self.assertIn('Value must be between 10s and 15m', str(cm.exception))

    def test_clean_fails_with_failover_delay_above_range(self):
        group = ZabbixProxyGroup(zabbixserver=self.zabbixserver, name='Too Long Delay', failover_delay='16m', min_online=2)

        with self.assertRaises(ValidationError) as cm:
            group.clean()
        self.assertIn('Value must be between 10s and 15m', str(cm.exception))

    def test_clean_fails_with_min_online_too_low(self):
        group = ZabbixProxyGroup(zabbixserver=self.zabbixserver, name='Too Low Online', failover_delay='1m', min_online=0)

        with self.assertRaises(ValidationError) as cm:
            group.clean()
        self.assertIn('min_online must be between 1 and 1000', str(cm.exception))

    def test_clean_fails_with_min_online_too_high(self):
        group = ZabbixProxyGroup(zabbixserver=self.zabbixserver, name='Too High Online', failover_delay='1m', min_online=1001)

        with self.assertRaises(ValidationError) as cm:
            group.clean()
        self.assertIn('min_online must be between 1 and 1000', str(cm.exception))
