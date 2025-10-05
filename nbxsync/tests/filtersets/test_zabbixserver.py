from django.test import TestCase

from nbxsync.filtersets import ZabbixServerFilterSet
from nbxsync.models import ZabbixServer


class ZabbixServerFilterSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.servers = [
            ZabbixServer.objects.create(
                name='Zabbix Prod',
                description='Production Zabbix',
                url='https://prod.zabbix.local',
                token='prod-token',
                validate_certs=True,
            ),
            ZabbixServer.objects.create(
                name='Zabbix Dev',
                description='Development Zabbix',
                url='https://dev.zabbix.local',
                token='dev-token',
                validate_certs=False,
            ),
        ]

    def test_search_by_name(self):
        f = ZabbixServerFilterSet({'q': 'Prod'}, queryset=ZabbixServer.objects.all())
        self.assertIn(self.servers[0], f.qs)
        self.assertNotIn(self.servers[1], f.qs)

    def test_search_by_description(self):
        f = ZabbixServerFilterSet({'q': 'Development'}, queryset=ZabbixServer.objects.all())
        self.assertIn(self.servers[1], f.qs)

    def test_blank_search_returns_all(self):
        f = ZabbixServerFilterSet({'q': ''}, queryset=ZabbixServer.objects.all())
        self.assertQuerySetEqual(f.qs.order_by('id'), ZabbixServer.objects.all().order_by('id'), transform=lambda x: x)

    def test_search_whitespace_direct_call(self):
        queryset = ZabbixServer.objects.all()
        f = ZabbixServerFilterSet({}, queryset=queryset)
        result = f.search(queryset, name='q', value='   ')
        self.assertQuerySetEqual(result.order_by('id'), queryset.order_by('id'), transform=lambda x: x)

    def test_filter_by_name_field(self):
        f = ZabbixServerFilterSet({'name': 'Dev'}, queryset=ZabbixServer.objects.all())
        self.assertIn(self.servers[1], f.qs)
        self.assertNotIn(self.servers[0], f.qs)

    def test_filter_by_description_field(self):
        f = ZabbixServerFilterSet({'description': 'Production'}, queryset=ZabbixServer.objects.all())
        self.assertIn(self.servers[0], f.qs)

    def test_filter_by_url_field(self):
        f = ZabbixServerFilterSet({'url': 'dev.zabbix'}, queryset=ZabbixServer.objects.all())
        self.assertIn(self.servers[1], f.qs)

    def test_filter_by_validate_certs_true(self):
        f = ZabbixServerFilterSet({'validate_certs': True}, queryset=ZabbixServer.objects.all())
        self.assertIn(self.servers[0], f.qs)
        self.assertNotIn(self.servers[1], f.qs)

    def test_filter_by_validate_certs_false(self):
        f = ZabbixServerFilterSet({'validate_certs': False}, queryset=ZabbixServer.objects.all())
        self.assertIn(self.servers[1], f.qs)
        self.assertNotIn(self.servers[0], f.qs)
