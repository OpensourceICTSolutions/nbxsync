from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.filtersets import ZabbixMacroAssignmentFilterSet
from nbxsync.models import ZabbixMacro, ZabbixMacroAssignment


class ZabbixMacroAssignmentFilterSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.macros = [
            ZabbixMacro.objects.create(macro='{$SNMP_COMMUNITY}', value='public', description='SNMP macro', type=1, hostmacroid='101'),
            ZabbixMacro.objects.create(macro='{$DB_USER}', value='admin', description='DB username', type=1, hostmacroid='102'),
        ]

        cls.devices = [
            create_test_device(name='HostInventory Test Device 1'),
            create_test_device(name='HostInventory Test Device 2'),
            create_test_device(name='HostInventory Test Device 3'),
            create_test_device(name='HostInventory Test Device 4'),
        ]

        cls.device_ct = ContentType.objects.get_for_model(Device)

        cls.assignments = [
            ZabbixMacroAssignment.objects.create(
                zabbixmacro=cls.macros[0],
                value='public',
                is_regex=False,
                context='dev',
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[0].id,
            ),
            ZabbixMacroAssignment.objects.create(
                zabbixmacro=cls.macros[1],
                value='admin',
                is_regex=True,
                context='vm',
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[0].id,
            ),
        ]

    def test_search_by_value(self):
        f = ZabbixMacroAssignmentFilterSet({'q': 'admin'}, queryset=ZabbixMacroAssignment.objects.all())
        self.assertIn(self.assignments[1], f.qs)
        self.assertNotIn(self.assignments[0], f.qs)

    def test_search_by_macro(self):
        f = ZabbixMacroAssignmentFilterSet({'q': 'SNMP'}, queryset=ZabbixMacroAssignment.objects.all())
        self.assertIn(self.assignments[0], f.qs)

    def test_search_blank_returns_all(self):
        f = ZabbixMacroAssignmentFilterSet({'q': ''}, queryset=ZabbixMacroAssignment.objects.all())
        self.assertEqual(f.qs.count(), 2)

    def test_search_whitespace_triggers_return_queryset(self):
        queryset = ZabbixMacroAssignment.objects.all()
        f = ZabbixMacroAssignmentFilterSet({}, queryset=queryset)
        result = f.search(queryset, name='q', value='   ')
        self.assertQuerySetEqual(result.order_by('id'), queryset.order_by('id'), transform=lambda x: x)

    def test_filter_by_zabbixmacro_macro(self):
        f = ZabbixMacroAssignmentFilterSet({'zabbixmacro_macro': 'DB_USER'}, queryset=ZabbixMacroAssignment.objects.all())
        self.assertIn(self.assignments[1], f.qs)

    def test_filter_by_value_field(self):
        f = ZabbixMacroAssignmentFilterSet({'value': 'public'}, queryset=ZabbixMacroAssignment.objects.all())
        self.assertIn(self.assignments[0], f.qs)

    def test_filter_by_context(self):
        f = ZabbixMacroAssignmentFilterSet({'context': 'vm'}, queryset=ZabbixMacroAssignment.objects.all())
        self.assertIn(self.assignments[1], f.qs)

    def test_filter_by_is_regex_true(self):
        f = ZabbixMacroAssignmentFilterSet({'is_regex': 'True'}, queryset=ZabbixMacroAssignment.objects.all())
        self.assertIn(self.assignments[1], f.qs)
        self.assertNotIn(self.assignments[0], f.qs)
