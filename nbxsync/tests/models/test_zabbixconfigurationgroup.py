from unittest.mock import MagicMock, patch
from django.core.exceptions import ValidationError
from django.test import TestCase

from nbxsync.models import ZabbixConfigurationGroup


class ZabbixConfigurationGroupTestCase(TestCase):
    def setUp(self):
        self.valid_data = {
            'name': 'SNMP Group',
            'description': 'Default configuration group used for SNMP setups',
        }

    def test_valid_configuration_group_creation(self):
        cfg = ZabbixConfigurationGroup(**self.valid_data)
        cfg.full_clean()
        cfg.save()
        self.assertEqual(ZabbixConfigurationGroup.objects.count(), 1)

    def test_missing_required_fields(self):
        required_fields = ['name']
        for field in required_fields:
            data = self.valid_data.copy()
            data.pop(field)
            cfg = ZabbixConfigurationGroup(**data)
            with self.assertRaises(ValidationError):
                cfg.full_clean()

    def test_optional_fields_can_be_blank(self):
        data = self.valid_data.copy()
        data['description'] = ''
        cfg = ZabbixConfigurationGroup(**data)
        cfg.full_clean()

    def test_str_method(self):
        cfg = ZabbixConfigurationGroup.objects.create(**self.valid_data)
        self.assertEqual(str(cfg), self.valid_data['name'])

    def test_ordering_by_created_desc(self):
        first = ZabbixConfigurationGroup.objects.create(name='Older Group', description='Created first')
        second = ZabbixConfigurationGroup.objects.create(name='Newer Group', description='Created second')
        objs = list(ZabbixConfigurationGroup.objects.all())
        self.assertEqual(objs[0], second)
        self.assertEqual(objs[1], first)

    def test_max_length_constraints(self):
        # name max_length=512
        data = self.valid_data.copy()
        data['name'] = 'a' * 513
        cfg = ZabbixConfigurationGroup(**data)
        with self.assertRaises(ValidationError) as cm:
            cfg.full_clean()
        self.assertIn('name', cm.exception.message_dict)

        # description max_length=1024
        data = self.valid_data.copy()
        data['description'] = 'b' * 1025
        cfg = ZabbixConfigurationGroup(**data)
        with self.assertRaises(ValidationError) as cm:
            cfg.full_clean()
        self.assertIn('description', cm.exception.message_dict)

    def test_resync_all_assignments_calls_helper_for_each_assignment(self):
        cfg = ZabbixConfigurationGroup.objects.create(**self.valid_data)

        assignment1 = object()
        assignment2 = object()

        with (
            patch.object(ZabbixConfigurationGroup, 'zabbixconfigurationgroupassignment') as mock_related,
            patch('nbxsync.utils.cfggroup.resync_zabbixconfiggroupassignment.resync_zabbixconfigurationgroupassignment') as mock_resync,
        ):
            mock_related.all.return_value = [assignment1, assignment2]

            cfg.resync_all_assignments()

        mock_related.all.assert_called_once_with()

        mock_resync.assert_any_call(assignment1)
        mock_resync.assert_any_call(assignment2)
        self.assertEqual(mock_resync.call_count, 2)
