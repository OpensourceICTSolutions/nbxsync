from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.models import ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment


class ZabbixConfigurationGroupAssignmentTestCase(TestCase):
    def setUp(self):
        self.cfg = ZabbixConfigurationGroup.objects.create(name='Default Config', description='Default configuration group')
        self.device = create_test_device(name='cfg-assignment-device-1')
        self.device_ct = ContentType.objects.get_for_model(Device)

        self.valid_data = {
            'zabbixconfigurationgroup': self.cfg,
            'assigned_object_type': self.device_ct,
            'assigned_object_id': self.device.id,
        }

    def test_valid_assignment_creation(self):
        obj = ZabbixConfigurationGroupAssignment(**self.valid_data)
        obj.full_clean()
        obj.save()
        self.assertEqual(ZabbixConfigurationGroupAssignment.objects.count(), 1)

    def test_missing_required_fields(self):
        data = self.valid_data.copy()
        data.pop('zabbixconfigurationgroup')
        obj = ZabbixConfigurationGroupAssignment(**data)
        with self.assertRaises(ValidationError):
            obj.full_clean()

    def test_assigned_object_fields_can_be_blank(self):
        data = {
            'zabbixconfigurationgroup': self.cfg,
            'assigned_object_type': None,
            'assigned_object_id': None,
        }
        obj = ZabbixConfigurationGroupAssignment(**data)
        obj.full_clean()

    def test_generic_foreign_key_resolves(self):
        obj = ZabbixConfigurationGroupAssignment.objects.create(**self.valid_data)
        self.assertIsNotNone(obj.assigned_object)
        self.assertEqual(obj.assigned_object.pk, self.device.pk)
        self.assertIsInstance(obj.assigned_object, Device)

    def test_uniqueness_constraint_per_object_same_group(self):
        ZabbixConfigurationGroupAssignment.objects.create(**self.valid_data)
        dup = ZabbixConfigurationGroupAssignment(**self.valid_data)
        with self.assertRaises(ValidationError) as cm:
            dup.full_clean()
        self.assertIn('__all__', cm.exception.message_dict)
        self.assertIn('Object can only be assigned once to a Zabbix Configuration Group', cm.exception.message_dict['__all__'])

    def test_uniqueness_allows_same_object_different_group(self):
        ZabbixConfigurationGroupAssignment.objects.create(**self.valid_data)

        other_group = ZabbixConfigurationGroup.objects.create(name='Agent Config', description='Agent profile')
        data = self.valid_data.copy()
        data['zabbixconfigurationgroup'] = other_group

        obj = ZabbixConfigurationGroupAssignment(**data)
        obj.full_clean()
        obj.save()
        self.assertEqual(ZabbixConfigurationGroupAssignment.objects.count(), 2)

    def test_uniqueness_allows_different_object_same_group(self):
        ZabbixConfigurationGroupAssignment.objects.create(**self.valid_data)

        other_device = create_test_device(name='cfg-assignment-device-2')
        data = self.valid_data.copy()
        data['assigned_object_id'] = other_device.id

        obj = ZabbixConfigurationGroupAssignment(**data)
        obj.full_clean()
        obj.save()
        self.assertEqual(ZabbixConfigurationGroupAssignment.objects.count(), 2)

    def test_str_method(self):
        obj = ZabbixConfigurationGroupAssignment.objects.create(**self.valid_data)
        self.assertEqual(str(obj), self.cfg.name)

    def test_ordering_by_created_desc(self):
        first = ZabbixConfigurationGroupAssignment.objects.create(**self.valid_data)

        other_device = create_test_device(name='cfg-assignment-device-3')
        second = ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=other_device.id)

        objs = list(ZabbixConfigurationGroupAssignment.objects.all())
        self.assertEqual(objs[0], second)
        self.assertEqual(objs[1], first)
