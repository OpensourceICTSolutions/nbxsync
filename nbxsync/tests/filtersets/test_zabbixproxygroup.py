from django.test import TestCase

from nbxsync.filtersets import ZabbixProxyGroupFilterSet
from nbxsync.models import ZabbixProxyGroup, ZabbixServer


class ZabbixProxyGroupFilterSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.servers = [
            ZabbixServer.objects.create(
                name='Zabbix Server A',
                url='http://a.local',
                token='a-token',
                validate_certs=True,
            ),
            ZabbixServer.objects.create(
                name='Zabbix Server B',
                url='http://b.local',
                token='b-token',
                validate_certs=True,
            ),
        ]

        cls.groups = [
            ZabbixProxyGroup.objects.create(
                name='Proxy Group One',
                proxy_groupid=10,
                min_online=1,
                failover_delay=60,
                zabbixserver=cls.servers[0],
                description='Primary proxy group',
            ),
            ZabbixProxyGroup.objects.create(
                name='Proxy Group Two',
                proxy_groupid=20,
                min_online=2,
                failover_delay=120,
                zabbixserver=cls.servers[1],
                description='Secondary proxy group',
            ),
        ]

    def test_search_by_name(self):
        f = ZabbixProxyGroupFilterSet({'q': 'One'}, queryset=ZabbixProxyGroup.objects.all())
        self.assertIn(self.groups[0], f.qs)
        self.assertNotIn(self.groups[1], f.qs)

    def test_search_by_description(self):
        f = ZabbixProxyGroupFilterSet({'q': 'Secondary'}, queryset=ZabbixProxyGroup.objects.all())
        self.assertIn(self.groups[1], f.qs)

    def test_search_blank_returns_all(self):
        f = ZabbixProxyGroupFilterSet({'q': ''}, queryset=ZabbixProxyGroup.objects.all())
        self.assertQuerySetEqual(f.qs.order_by('id'), ZabbixProxyGroup.objects.all().order_by('id'), transform=lambda x: x)

    def test_search_whitespace_direct(self):
        f = ZabbixProxyGroupFilterSet({}, queryset=ZabbixProxyGroup.objects.all())
        result = f.search(ZabbixProxyGroup.objects.all(), name='q', value='   ')
        self.assertQuerySetEqual(result.order_by('id'), ZabbixProxyGroup.objects.all().order_by('id'), transform=lambda x: x)

    def test_filter_by_name(self):
        f = ZabbixProxyGroupFilterSet({'name': 'Two'}, queryset=ZabbixProxyGroup.objects.all())
        self.assertIn(self.groups[1], f.qs)

    def test_filter_by_proxy_groupid(self):
        f = ZabbixProxyGroupFilterSet({'proxy_groupid': 10}, queryset=ZabbixProxyGroup.objects.all())
        self.assertIn(self.groups[0], f.qs)

    def test_filter_by_min_online(self):
        f = ZabbixProxyGroupFilterSet({'min_online': 2}, queryset=ZabbixProxyGroup.objects.all())
        self.assertIn(self.groups[1], f.qs)

    def test_filter_by_failover_delay(self):
        f = ZabbixProxyGroupFilterSet({'failover_delay': 60}, queryset=ZabbixProxyGroup.objects.all())
        self.assertIn(self.groups[0], f.qs)

    def test_filter_by_zabbixserver(self):
        f = ZabbixProxyGroupFilterSet({'zabbixserver': self.servers[0].id}, queryset=ZabbixProxyGroup.objects.all())
        self.assertIn(self.groups[0], f.qs)
        self.assertNotIn(self.groups[1], f.qs)

    def test_filter_by_zabbixserver_name(self):
        f = ZabbixProxyGroupFilterSet({'zabbixserver_name': 'Server B'}, queryset=ZabbixProxyGroup.objects.all())
        self.assertIn(self.groups[1], f.qs)
