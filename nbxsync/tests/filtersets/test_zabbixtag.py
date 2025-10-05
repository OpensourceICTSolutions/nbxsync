from django.test import TestCase

from nbxsync.filtersets import ZabbixTagFilterSet
from nbxsync.models import ZabbixTag


class ZabbixTagFilterSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tags = [
            ZabbixTag.objects.create(name='Service', description='Tagged for monitoring', tag='service', value='web'),
            ZabbixTag.objects.create(name='Location', description='', tag='location', value='datacenter-1'),
            ZabbixTag.objects.create(name='App', description='Critical application', tag='application', value='nginx'),
        ]

    def test_search_matches_name(self):
        f = ZabbixTagFilterSet({'q': 'Service'}, queryset=ZabbixTag.objects.all())
        self.assertIn(self.tags[0], f.qs)
        self.assertNotIn(self.tags[1], f.qs)

    def test_search_matches_description(self):
        f = ZabbixTagFilterSet({'q': 'Critical'}, queryset=ZabbixTag.objects.all())
        self.assertIn(self.tags[2], f.qs)

    def test_search_matches_tag(self):
        f = ZabbixTagFilterSet({'q': 'location'}, queryset=ZabbixTag.objects.all())
        self.assertIn(self.tags[1], f.qs)

    def test_search_matches_value(self):
        f = ZabbixTagFilterSet({'q': 'nginx'}, queryset=ZabbixTag.objects.all())
        self.assertIn(self.tags[2], f.qs)

    def test_search_with_blank_string_returns_all(self):
        queryset = ZabbixTag.objects.all()
        f = ZabbixTagFilterSet({'q': ''}, queryset=queryset)
        self.assertQuerySetEqual(f.qs.order_by('pk'), queryset.order_by('pk'), transform=lambda x: x)

    def test_search_method_directly_covers_return_queryset(self):
        queryset = ZabbixTag.objects.all()
        f = ZabbixTagFilterSet({}, queryset=queryset)
        result = f.search(queryset, name='q', value='   ')  # whitespace triggers early return
        self.assertQuerySetEqual(result.order_by('pk'), queryset.order_by('pk'), transform=lambda x: x)

    def test_filter_by_name_icontains(self):
        f = ZabbixTagFilterSet({'name': 'loc'}, queryset=ZabbixTag.objects.all())
        self.assertIn(self.tags[1], f.qs)

    def test_filter_by_description_icontains(self):
        f = ZabbixTagFilterSet({'description': 'monitor'}, queryset=ZabbixTag.objects.all())
        self.assertIn(self.tags[0], f.qs)

    def test_filter_by_tag_icontains(self):
        f = ZabbixTagFilterSet({'tag': 'service'}, queryset=ZabbixTag.objects.all())
        self.assertIn(self.tags[0], f.qs)

    def test_filter_by_value_icontains(self):
        f = ZabbixTagFilterSet({'value': 'data'}, queryset=ZabbixTag.objects.all())
        self.assertIn(self.tags[1], f.qs)
