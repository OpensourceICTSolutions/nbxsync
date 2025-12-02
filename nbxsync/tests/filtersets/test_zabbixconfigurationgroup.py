from django.test import TestCase

from nbxsync.filtersets import ZabbixConfigurationGroupFilterSet
from nbxsync.models import ZabbixConfigurationGroup


class ZabbixConfigurationGroupFilterSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cfg1 = ZabbixConfigurationGroup.objects.create(
            name='SNMP configuration',
            description='Default configuration group for all SNMP hosts',
        )
        cls.cfg2 = ZabbixConfigurationGroup.objects.create(
            name='Agent Profile',
            description='Demo group for agent setups',
        )
        cls.cfg3 = ZabbixConfigurationGroup.objects.create(
            name='JMX Config',
            description='Something Something configuration',
        )

    def test_filter_by_name_icontains(self):
        params = {'name': 'SNMP'}
        f = ZabbixConfigurationGroupFilterSet(params, ZabbixConfigurationGroup.objects.all())
        self.assertEqual(list(f.qs), [self.cfg1])

    def test_filter_by_description_icontains(self):
        params = {'description': 'agent'}
        f = ZabbixConfigurationGroupFilterSet(params, ZabbixConfigurationGroup.objects.all())
        self.assertEqual(list(f.qs), [self.cfg2])

    def test_search_by_name(self):
        params = {'q': 'JMX'}
        f = ZabbixConfigurationGroupFilterSet(params, ZabbixConfigurationGroup.objects.all())
        self.assertEqual(list(f.qs), [self.cfg3])

    def test_search_by_description(self):
        params = {'q': 'default'}
        f = ZabbixConfigurationGroupFilterSet(params, ZabbixConfigurationGroup.objects.all())
        self.assertEqual(list(f.qs), [self.cfg1])

    def test_search_case_insensitive(self):
        params = {'q': 'aGent'}
        f = ZabbixConfigurationGroupFilterSet(params, ZabbixConfigurationGroup.objects.all())
        self.assertEqual(list(f.qs), [self.cfg2])

    def test_search_returns_all_when_blank(self):
        params = {'q': '   '}  # Only spaces
        f = ZabbixConfigurationGroupFilterSet(params, ZabbixConfigurationGroup.objects.all())
        # Should return all three since no filter applied
        self.assertEqual(set(f.qs), {self.cfg1, self.cfg2, self.cfg3})

    def test_search_matches_multiple_fields(self):
        # "config" appears in both cfg1.name and cfg3.name
        params = {'q': 'configuration'}
        f = ZabbixConfigurationGroupFilterSet(params, ZabbixConfigurationGroup.objects.all())
        self.assertEqual(set(f.qs), {self.cfg1, self.cfg3})

    def test_search_returns_original_queryset_when_blank_spaces(self):
        base_qs = ZabbixConfigurationGroup.objects.all()
        f = ZabbixConfigurationGroupFilterSet({}, base_qs)

        result_qs = f.search(base_qs, 'q', '   ')  # whitespace-only
        self.assertEqual(str(result_qs.query), str(base_qs.query))

    def test_search_returns_original_queryset_when_empty_string(self):
        base_qs = ZabbixConfigurationGroup.objects.all()
        f = ZabbixConfigurationGroupFilterSet({}, base_qs)

        result_qs = f.search(base_qs, 'q', '')  # empty string
        self.assertEqual(str(result_qs.query), str(base_qs.query))
