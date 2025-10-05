from django.test import TestCase

from nbxsync.choices import ZabbixProxyTypeChoices
from nbxsync.filtersets import ZabbixProxyFilterSet
from nbxsync.models import ZabbixProxy, ZabbixProxyGroup, ZabbixServer


class ZabbixProxyFilterSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.zabbix_servers = [
            ZabbixServer.objects.create(name='Zabbix Server A', url='http://a.local', token='a-token'),
            ZabbixServer.objects.create(name='Zabbix Server B', url='http://b.local', token='b-token'),
        ]

        cls.proxy_groups = [
            ZabbixProxyGroup.objects.create(name='Proxy Group A', zabbixserver=cls.zabbix_servers[0]),
            ZabbixProxyGroup.objects.create(name='Proxy Group B', zabbixserver=cls.zabbix_servers[1]),
        ]

        cls.proxies = [
            ZabbixProxy.objects.create(
                name='Proxy Alpha',
                zabbixserver=cls.zabbix_servers[0],
                proxygroup=cls.proxy_groups[0],
                operating_mode=ZabbixProxyTypeChoices.ACTIVE,
                local_address='10.0.0.1',
                address='proxy-alpha.local',
            ),
            ZabbixProxy.objects.create(
                name='Proxy Beta',
                zabbixserver=cls.zabbix_servers[1],
                proxygroup=cls.proxy_groups[1],
                operating_mode=ZabbixProxyTypeChoices.PASSIVE,
                local_address='10.0.0.2',
                address='proxy-beta.local',
            ),
        ]

    def test_filter_by_search_name(self):
        f = ZabbixProxyFilterSet({'q': 'Alpha'}, queryset=ZabbixProxy.objects.all())
        self.assertIn(self.proxies[0], f.qs)
        self.assertNotIn(self.proxies[1], f.qs)

    def test_filter_by_search_address(self):
        f = ZabbixProxyFilterSet({'q': 'proxy-beta'}, queryset=ZabbixProxy.objects.all())
        self.assertIn(self.proxies[1], f.qs)
        self.assertNotIn(self.proxies[0], f.qs)

    def test_filter_by_search_local_address(self):
        f = ZabbixProxyFilterSet({'q': '10.0.0.1'}, queryset=ZabbixProxy.objects.all())
        self.assertIn(self.proxies[0], f.qs)
        self.assertNotIn(self.proxies[1], f.qs)

    def test_filter_by_name_icontains(self):
        f = ZabbixProxyFilterSet({'name': 'alpha'}, queryset=ZabbixProxy.objects.all())
        self.assertIn(self.proxies[0], f.qs)
        self.assertNotIn(self.proxies[1], f.qs)

    def test_filter_by_proxygroup_name(self):
        f = ZabbixProxyFilterSet({'proxygroup_name': 'Group A'}, queryset=ZabbixProxy.objects.all())
        self.assertIn(self.proxies[0], f.qs)
        self.assertNotIn(self.proxies[1], f.qs)

    def test_filter_by_zabbixserver(self):
        f = ZabbixProxyFilterSet({'zabbixserver': self.zabbix_servers[0].pk}, queryset=ZabbixProxy.objects.all())
        self.assertIn(self.proxies[0], f.qs)
        self.assertNotIn(self.proxies[1], f.qs)

    def test_filter_by_operating_mode(self):
        f = ZabbixProxyFilterSet({'operating_mode': ZabbixProxyTypeChoices.PASSIVE}, queryset=ZabbixProxy.objects.all())
        self.assertIn(self.proxies[1], f.qs)
        self.assertNotIn(self.proxies[0], f.qs)

    def test_search_method_with_blank_value_returns_queryset(self):
        queryset = ZabbixProxy.objects.all()
        filterset = ZabbixProxyFilterSet({}, queryset=queryset)

        # Directly invoke the method to cover the `if not value.strip():` branch
        result = filterset.search(queryset, name='q', value='   ')

        self.assertQuerySetEqual(result.order_by('pk'), queryset.order_by('pk'), transform=lambda x: x)
