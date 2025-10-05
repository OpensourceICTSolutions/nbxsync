from django.test import TestCase

from nbxsync.filtersets import ZabbixMacroFilterSet
from nbxsync.models import ZabbixMacro


class ZabbixMacroFilterSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.macros = [
            ZabbixMacro.objects.create(macro='{$SNMP_COMMUNITY}', value='public', description='SNMP macro', type=0, hostmacroid='1234'),
            ZabbixMacro.objects.create(macro='{$DB_USER}', value='postgres', description='Database user', type=0, hostmacroid='5678'),
        ]

    def test_search_by_macro(self):
        f = ZabbixMacroFilterSet({'q': 'SNMP'}, queryset=ZabbixMacro.objects.all())
        self.assertIn(self.macros[0], f.qs)
        self.assertNotIn(self.macros[1], f.qs)

    def test_search_by_hostmacroid(self):
        f = ZabbixMacroFilterSet({'q': '5678'}, queryset=ZabbixMacro.objects.all())
        self.assertIn(self.macros[1], f.qs)

    def test_search_blank_returns_all(self):
        f = ZabbixMacroFilterSet({'q': ''}, queryset=ZabbixMacro.objects.all())
        self.assertQuerySetEqual(f.qs.order_by('id'), ZabbixMacro.objects.all().order_by('id'), transform=lambda x: x)

    def test_direct_search_method_blank(self):
        queryset = ZabbixMacro.objects.all()
        f = ZabbixMacroFilterSet({}, queryset=queryset)
        result = f.search(queryset, name='q', value='   ')
        self.assertQuerySetEqual(result.order_by('id'), queryset.order_by('id'), transform=lambda x: x)

    def test_filter_by_macro(self):
        f = ZabbixMacroFilterSet({'macro': 'DB_USER'}, queryset=ZabbixMacro.objects.all())
        self.assertIn(self.macros[1], f.qs)

    def test_filter_by_value(self):
        f = ZabbixMacroFilterSet({'value': 'public'}, queryset=ZabbixMacro.objects.all())
        self.assertIn(self.macros[0], f.qs)

    def test_filter_by_description(self):
        f = ZabbixMacroFilterSet({'description': 'SNMP'}, queryset=ZabbixMacro.objects.all())
        self.assertIn(self.macros[0], f.qs)

    def test_filter_by_type(self):
        f = ZabbixMacroFilterSet({'type': 0}, queryset=ZabbixMacro.objects.all())
        self.assertEqual(f.qs.count(), 2)

    def test_filter_by_hostmacroid(self):
        f = ZabbixMacroFilterSet({'hostmacroid': '5678'}, queryset=ZabbixMacro.objects.all())
        self.assertIn(self.macros[1], f.qs)
