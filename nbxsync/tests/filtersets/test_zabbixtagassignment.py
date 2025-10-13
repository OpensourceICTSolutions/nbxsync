from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.filtersets import ZabbixTagAssignmentFilterSet
from nbxsync.models import ZabbixTag, ZabbixTagAssignment


class ZabbixTagAssignmentFilterSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tag1 = ZabbixTag.objects.create(name='Environment', tag='env', value='prod')
        cls.tag2 = ZabbixTag.objects.create(name='Role', tag='role', value='web')

        cls.devices = [
            create_test_device(name='Zabbix Tag Test Device 1'),
            create_test_device(name='Zabbix Tag Test Device 2'),
            create_test_device(name='Zabbix Tag Test Device 3'),
            create_test_device(name='Zabbix Tag Test Device 4'),
        ]

        cls.device_ct = ContentType.objects.get_for_model(Device)
        cls.assignments = [
            ZabbixTagAssignment.objects.create(zabbixtag=cls.tag1, assigned_object_type=cls.device_ct, assigned_object_id=cls.devices[0].id),
            ZabbixTagAssignment.objects.create(zabbixtag=cls.tag2, assigned_object_type=cls.device_ct, assigned_object_id=cls.devices[1].id),
        ]

    def test_search_by_tag_name(self):
        f = ZabbixTagAssignmentFilterSet({'q': 'Environment'}, queryset=ZabbixTagAssignment.objects.all())
        self.assertIn(self.assignments[0], f.qs)
        self.assertNotIn(self.assignments[1], f.qs)

    def test_search_by_tag_field(self):
        f = ZabbixTagAssignmentFilterSet({'q': 'role'}, queryset=ZabbixTagAssignment.objects.all())
        self.assertIn(self.assignments[1], f.qs)

    def test_blank_search_returns_all(self):
        queryset = ZabbixTagAssignment.objects.all()
        f = ZabbixTagAssignmentFilterSet({'q': ''}, queryset=queryset)
        self.assertQuerySetEqual(f.qs.order_by('id'), queryset.order_by('id'), transform=lambda x: x)

    def test_search_method_direct_call_hits_return_queryset(self):
        queryset = ZabbixTagAssignment.objects.all()
        f = ZabbixTagAssignmentFilterSet({}, queryset=queryset)
        result = f.search(queryset, name='q', value='   ')
        self.assertQuerySetEqual(result.order_by('id'), queryset.order_by('id'), transform=lambda x: x)

    def test_filter_by_zabbixtag_name(self):
        f = ZabbixTagAssignmentFilterSet({'zabbixtag_name': 'Role'}, queryset=ZabbixTagAssignment.objects.all())
        self.assertIn(self.assignments[1], f.qs)
        self.assertNotIn(self.assignments[0], f.qs)

    def test_filter_by_zabbixtag_tag(self):
        f = ZabbixTagAssignmentFilterSet({'zabbixtag_tag': 'env'}, queryset=ZabbixTagAssignment.objects.all())
        self.assertIn(self.assignments[0], f.qs)

    def test_filter_by_assigned_object_type(self):
        f = ZabbixTagAssignmentFilterSet({'assigned_object_type': f'{self.device_ct.app_label}.{self.device_ct.model}'}, queryset=ZabbixTagAssignment.objects.all())
        self.assertEqual(f.qs.count(), 2)

    def test_filter_fails_with_wrong_content_type(self):
        wrong_ct = ContentType.objects.get_for_model(ZabbixTag)
        f = ZabbixTagAssignmentFilterSet(
            {'assigned_object_type': f'{wrong_ct.app_label}.{wrong_ct.model}', 'assigned_object_id': self.devices[0].id},
            queryset=ZabbixTagAssignment.objects.all(),
        )
        self.assertEqual(f.qs.count(), 0)

    def test_filter_by_assigned_object_id_alone(self):
        f = ZabbixTagAssignmentFilterSet({'assigned_object_id': self.devices[0].id}, queryset=ZabbixTagAssignment.objects.all())
        self.assertIn(self.assignments[0], f.qs)
        self.assertNotIn(self.assignments[1], f.qs)
