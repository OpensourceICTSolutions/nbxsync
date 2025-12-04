from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase

from utilities.testing import create_test_device

from nbxsync.choices import ZabbixHostInventoryModeChoices
from nbxsync.models import ZabbixHostInventory


class ZabbixHostInventoryTestCase(TestCase):
    def setUp(self):
        self.device = create_test_device(name='Device 1')
        self.content_type = ContentType.objects.get_for_model(self.device)

        self.valid_data = {
            'assigned_object_type': self.content_type,
            'assigned_object_id': self.device.pk,
            'inventory_mode': ZabbixHostInventoryModeChoices.MANUAL,
            'alias': 'Test {{ object.name }} Alias',
            'hardware': 'Server',
        }

    def test_valid_inventory_creation(self):
        inventory = ZabbixHostInventory(**self.valid_data)
        inventory.full_clean()
        inventory.save()
        self.assertEqual(ZabbixHostInventory.objects.count(), 1)
        self.assertEqual(str(inventory), f'Host Inventory of {self.device.name}')

    def test_missing_assigned_object_raises(self):
        data = self.valid_data.copy()
        data['assigned_object_type'] = None
        data['assigned_object_id'] = None
        inventory = ZabbixHostInventory(**data)
        with self.assertRaises(ValidationError) as cm:
            inventory.full_clean()
        self.assertIn('An assigned object must be provided', str(cm.exception))

    def test_uniqueness_constraint(self):
        ZabbixHostInventory.objects.create(**self.valid_data)
        duplicate = ZabbixHostInventory(**self.valid_data)
        with self.assertRaises(ValidationError) as cm:
            duplicate.full_clean()
        self.assertIn('Only one inventory entry is allowed per assigned object.', str(cm.exception))

    def test_get_inventory_mode(self):
        inventory = ZabbixHostInventory.objects.create(**self.valid_data)
        self.assertEqual(inventory.get_inventory_mode(), 'Manual')

    def test_render_field_success(self):
        inventory = ZabbixHostInventory.objects.create(**self.valid_data)
        rendered_value, success = inventory.render_field('alias')
        self.assertTrue(success)
        self.assertEqual(rendered_value, f'Test {self.device.name} Alias')

    def test_render_field_failure(self):
        self.valid_data['alias'] = '{{ undefined.attribute }}'
        inventory = ZabbixHostInventory.objects.create(**self.valid_data)
        rendered_value, success = inventory.render_field('alias')
        self.assertFalse(success)
        self.assertEqual(rendered_value, '')

    def test_render_all_fields(self):
        inventory = ZabbixHostInventory.objects.create(**self.valid_data)
        rendered = inventory.render_all_fields()
        self.assertIn('alias', rendered)
        alias_rendered, success = rendered['alias']
        self.assertTrue(success)
        self.assertEqual(alias_rendered, f'Test {self.device.name} Alias')

    def test_render_field_truncates_long_value(self):
        long_value = '{{ "A" * 200 }}'
        data = self.valid_data.copy()
        data['alias'] = long_value
        inventory = ZabbixHostInventory.objects.create(**data)

        rendered_value, success = inventory.render_field('alias')
        self.assertTrue(success)
        self.assertEqual(len(rendered_value), 128)
        self.assertEqual(rendered_value, 'A' * 128)

    @patch('nbxsync.models.zabbixhostinventory.render_jinja2', side_effect=Exception('Unexpected!'))
    def test_render_field_handles_unexpected_exception(self, mock_render):
        data = self.valid_data.copy()
        data['alias'] = '{{ any }}'
        inventory = ZabbixHostInventory.objects.create(**data)

        rendered_value, success = inventory.render_field('alias')
        self.assertFalse(success)
        self.assertEqual(rendered_value, '')
