from django.test import TestCase

from nbxsync.choices import HostInterfaceRequirementChoices
from nbxsync.filtersets import ZabbixTemplateFilterSet
from nbxsync.models import ZabbixServer, ZabbixTemplate


class ZabbixTemplateFilterSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.servers = [
            ZabbixServer.objects.create(name='Zabbix Server A', url='http://a.local', token='a-token', validate_certs=True),
            ZabbixServer.objects.create(name='Zabbix Server B', url='http://b.local', token='b-token', validate_certs=True),
        ]

        cls.templates = [
            ZabbixTemplate.objects.create(
                name='Linux Monitoring',
                templateid=1001,
                zabbixserver=cls.servers[0],
                interface_requirements=[HostInterfaceRequirementChoices.AGENT],
            ),
            ZabbixTemplate.objects.create(
                name='Database Monitoring',
                templateid=1002,
                zabbixserver=cls.servers[1],
                interface_requirements=[HostInterfaceRequirementChoices.SNMP],
            ),
        ]

    def test_search_by_name(self):
        f = ZabbixTemplateFilterSet({'q': 'linux'}, queryset=ZabbixTemplate.objects.all())
        self.assertIn(self.templates[0], f.qs)
        self.assertNotIn(self.templates[1], f.qs)

    def test_search_by_templateid(self):
        f = ZabbixTemplateFilterSet({'q': '1002'}, queryset=ZabbixTemplate.objects.all())
        self.assertIn(self.templates[1], f.qs)

    def test_search_by_server_name(self):
        f = ZabbixTemplateFilterSet({'q': 'Server A'}, queryset=ZabbixTemplate.objects.all())
        self.assertIn(self.templates[0], f.qs)

    def test_search_blank_returns_all(self):
        queryset = ZabbixTemplate.objects.all()
        f = ZabbixTemplateFilterSet({'q': ''}, queryset=queryset)
        self.assertQuerySetEqual(f.qs.order_by('pk'), queryset.order_by('pk'), transform=lambda x: x)

    def test_search_method_direct_blank_value(self):
        queryset = ZabbixTemplate.objects.all()
        f = ZabbixTemplateFilterSet({}, queryset=queryset)
        result = f.search(queryset, name='q', value='   ')
        self.assertQuerySetEqual(result.order_by('pk'), queryset.order_by('pk'), transform=lambda x: x)

    def test_filter_by_name(self):
        f = ZabbixTemplateFilterSet({'name': 'database'}, queryset=ZabbixTemplate.objects.all())
        self.assertIn(self.templates[1], f.qs)
        self.assertNotIn(self.templates[0], f.qs)

    def test_filter_by_templateid(self):
        f = ZabbixTemplateFilterSet({'templateid': 1001}, queryset=ZabbixTemplate.objects.all())
        self.assertIn(self.templates[0], f.qs)

    def test_filter_by_zabbixserver_name(self):
        f = ZabbixTemplateFilterSet({'zabbixserver_name': 'Server B'}, queryset=ZabbixTemplate.objects.all())
        self.assertIn(self.templates[1], f.qs)

    def test_filter_by_zabbixserver_id(self):
        f = ZabbixTemplateFilterSet({'zabbixserver': self.servers[0].id}, queryset=ZabbixTemplate.objects.all())
        self.assertIn(self.templates[0], f.qs)
        self.assertNotIn(self.templates[1], f.qs)
