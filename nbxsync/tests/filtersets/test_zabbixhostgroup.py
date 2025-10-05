from django.test import TestCase

from nbxsync.filtersets import ZabbixHostgroupFilterSet
from nbxsync.models import ZabbixHostgroup, ZabbixServer


class ZabbixHostgroupFilterSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.servers = [
            ZabbixServer.objects.create(
                name='Server A',
                url='http://a.example.com',
                token='token-a',
                validate_certs=True,
            ),
            ZabbixServer.objects.create(
                name='Server B',
                url='http://b.example.com',
                token='token-b',
                validate_certs=True,
            ),
        ]

        cls.hostgroups = [
            ZabbixHostgroup.objects.create(
                name='Linux Servers',
                description='All Linux hosts',
                value='group-linux',
                groupid=101,
                zabbixserver=cls.servers[0],
            ),
            ZabbixHostgroup.objects.create(
                name='Database Servers',
                description='DB hosts',
                value='group-db',
                groupid=202,
                zabbixserver=cls.servers[1],
            ),
        ]

    def test_q_search_by_name(self):
        f = ZabbixHostgroupFilterSet({'q': 'Linux'}, queryset=ZabbixHostgroup.objects.all())
        self.assertIn(self.hostgroups[0], f.qs)
        self.assertNotIn(self.hostgroups[1], f.qs)

    def test_q_search_by_zabbixserver_name(self):
        f = ZabbixHostgroupFilterSet({'q': 'Server B'}, queryset=ZabbixHostgroup.objects.all())
        self.assertIn(self.hostgroups[1], f.qs)

    def test_q_search_by_groupid_numeric(self):
        f = ZabbixHostgroupFilterSet({'q': '101'}, queryset=ZabbixHostgroup.objects.all())
        self.assertIn(self.hostgroups[0], f.qs)

    def test_search_with_blank_value_returns_all(self):
        queryset = ZabbixHostgroup.objects.all()
        f = ZabbixHostgroupFilterSet({'q': ''}, queryset=queryset)
        self.assertQuerySetEqual(f.qs.order_by('pk'), queryset.order_by('pk'), transform=lambda x: x)

    def test_search_method_directly_hits_return_queryset(self):
        queryset = ZabbixHostgroup.objects.all()
        f = ZabbixHostgroupFilterSet({}, queryset=queryset)
        result = f.search(queryset, name='q', value='   ')
        self.assertQuerySetEqual(result.order_by('pk'), queryset.order_by('pk'), transform=lambda x: x)

    def test_q_search_whitespace_only(self):
        f = ZabbixHostgroupFilterSet({'q': '   '}, queryset=ZabbixHostgroup.objects.all())
        self.assertEqual(f.qs.count(), 2)

    def test_q_search_non_numeric_value_fallback(self):
        f = ZabbixHostgroupFilterSet({'q': 'Database'}, queryset=ZabbixHostgroup.objects.all())
        self.assertIn(self.hostgroups[1], f.qs)

    def test_filter_by_name(self):
        f = ZabbixHostgroupFilterSet({'name': 'Database'}, queryset=ZabbixHostgroup.objects.all())
        self.assertIn(self.hostgroups[1], f.qs)

    def test_filter_by_description(self):
        f = ZabbixHostgroupFilterSet({'description': 'Linux'}, queryset=ZabbixHostgroup.objects.all())
        self.assertIn(self.hostgroups[0], f.qs)

    def test_filter_by_value(self):
        f = ZabbixHostgroupFilterSet({'value': 'group-linux'}, queryset=ZabbixHostgroup.objects.all())
        self.assertIn(self.hostgroups[0], f.qs)

    def test_filter_by_groupid(self):
        f = ZabbixHostgroupFilterSet({'groupid': '202'}, queryset=ZabbixHostgroup.objects.all())
        self.assertIn(self.hostgroups[1], f.qs)

    def test_filter_by_zabbixserver_name_field(self):
        f = ZabbixHostgroupFilterSet({'zabbixserver_name': 'Server A'}, queryset=ZabbixHostgroup.objects.all())
        self.assertIn(self.hostgroups[0], f.qs)

    def test_search_blank_value_returns_queryset(self):
        queryset = ZabbixHostgroup.objects.all()
        f = ZabbixHostgroupFilterSet({'q': '   '}, queryset=queryset)
        self.assertQuerySetEqual(f.qs.order_by('id'), queryset.order_by('id'), transform=lambda x: x)

    def test_search_hits_name_or_servername_and_skips_groupid(self):
        f = ZabbixHostgroupFilterSet({'q': 'Linux'}, queryset=ZabbixHostgroup.objects.all())
        self.assertIn(self.hostgroups[0], f.qs)
        self.assertNotIn(self.hostgroups[1], f.qs)

    def test_filter_is_template_true_returns_only_templated(self):
        # Create a hostgroup whose value matches the Jinja pattern
        templated = ZabbixHostgroup.objects.create(
            name='Templated Group',
            description='Uses template',
            value='apply-to-{{ hostname }}',
            groupid=303,
            zabbixserver=self.servers[0],
        )

        f = ZabbixHostgroupFilterSet({'is_template': 'true'}, queryset=ZabbixHostgroup.objects.all())
        qs = list(f.qs)

        self.assertIn(templated, qs)
        # Existing non-templated objects should not be in the result
        self.assertNotIn(self.hostgroups[0], qs)
        self.assertNotIn(self.hostgroups[1], qs)

    def test_filter_is_template_false_excludes_templated(self):
        # Create a templated hostgroup
        templated = ZabbixHostgroup.objects.create(
            name='Templated Group 2',
            description='Uses template',
            value='{% if env %}group-{{ env }}{% endif %}',
            groupid=404,
            zabbixserver=self.servers[0],
        )

        f = ZabbixHostgroupFilterSet({'is_template': 'false'}, queryset=ZabbixHostgroup.objects.all())
        qs = list(f.qs)

        # Non-templated hostgroups should be present
        self.assertIn(self.hostgroups[0], qs)
        self.assertIn(self.hostgroups[1], qs)
        # Templated one should be excluded
        self.assertNotIn(templated, qs)
