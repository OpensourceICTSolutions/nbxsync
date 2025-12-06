from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.filtersets import ZabbixConfigurationGroupAssignmentFilterSet
from nbxsync.models import (
    ZabbixConfigurationGroup,
    ZabbixConfigurationGroupAssignment,
)


class ZabbixConfigurationGroupAssignmentFilterSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Two configuration groups
        cls.cfg1 = ZabbixConfigurationGroup.objects.create(
            name='Baseline Config',
            description='Default baseline',
        )
        cls.cfg2 = ZabbixConfigurationGroup.objects.create(
            name='Hardened Profile',
            description='Security hardened',
        )

        # Two devices (same content type)
        cls.dev1 = create_test_device(name='filter-assign-dev-1')
        cls.dev2 = create_test_device(name='filter-assign-dev-2')
        cls.device_ct = ContentType.objects.get_for_model(Device)

        # Two assignments
        cls.asn1 = ZabbixConfigurationGroupAssignment.objects.create(
            zabbixconfigurationgroup=cls.cfg1,
            assigned_object_type=cls.device_ct,
            assigned_object_id=cls.dev1.id,
        )
        cls.asn2 = ZabbixConfigurationGroupAssignment.objects.create(
            zabbixconfigurationgroup=cls.cfg2,
            assigned_object_type=cls.device_ct,
            assigned_object_id=cls.dev2.id,
        )

    def test_filter_by_zabbixconfigurationgroup_name_icontains(self):
        params = {'zabbixconfigurationgroup_name': 'Baseline'}
        f = ZabbixConfigurationGroupAssignmentFilterSet(params, ZabbixConfigurationGroupAssignment.objects.all())
        self.assertEqual(list(f.qs), [self.asn1])

        params = {'zabbixconfigurationgroup_name': 'hardened'}
        f = ZabbixConfigurationGroupAssignmentFilterSet(params, ZabbixConfigurationGroupAssignment.objects.all())
        self.assertEqual(list(f.qs), [self.asn2])

    def test_filter_by_assigned_object_type(self):
        # ContentTypeFilter typically expects "app_label.model" form
        params = {'assigned_object_type': f'{self.device_ct.app_label}.{self.device_ct.model}'}
        f = ZabbixConfigurationGroupAssignmentFilterSet(params, ZabbixConfigurationGroupAssignment.objects.all())
        self.assertEqual(set(f.qs), {self.asn1, self.asn2})

    def test_filter_by_assigned_object_id(self):
        params = {'assigned_object_id': self.dev1.id}
        f = ZabbixConfigurationGroupAssignmentFilterSet(params, ZabbixConfigurationGroupAssignment.objects.all())
        self.assertEqual(list(f.qs), [self.asn1])

    def test_search_by_group_name(self):
        params = {'q': 'Profile'}
        f = ZabbixConfigurationGroupAssignmentFilterSet(params, ZabbixConfigurationGroupAssignment.objects.all())
        self.assertEqual(list(f.qs), [self.asn2])

        params = {'q': 'Baseline'}
        f = ZabbixConfigurationGroupAssignmentFilterSet(params, ZabbixConfigurationGroupAssignment.objects.all())
        self.assertEqual(list(f.qs), [self.asn1])

    def test_search_is_blank_returns_original_queryset(self):
        base_qs = ZabbixConfigurationGroupAssignment.objects.all()
        # whitespace-only
        f = ZabbixConfigurationGroupAssignmentFilterSet({'q': '   '}, base_qs)
        self.assertEqual(set(f.qs), set(base_qs))

        # empty string through direct method call to hit the guard branch explicitly
        result_qs = ZabbixConfigurationGroupAssignmentFilterSet({}, base_qs).search(base_qs, 'q', '')
        self.assertEqual(str(result_qs.query), str(base_qs.query))
