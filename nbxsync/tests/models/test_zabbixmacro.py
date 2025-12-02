from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase

from nbxsync.choices import ZabbixMacroTypeChoices
from nbxsync.models import ZabbixMacro, ZabbixServer


class ZabbixMacroTestCase(TestCase):
    def setUp(self):
        self.zabbixserver = ZabbixServer.objects.create(name='Zabbix Server', url='http://127.0.0.1', token='fakeToken')

        self.content_type = ContentType.objects.get_for_model(ZabbixServer)
        self.valid_data = {
            'macro': 'TEST_MACRO',
            'value': 'value',
            'description': 'Test macro',
            'hostmacroid': 123,
            'type': ZabbixMacroTypeChoices.TEXT,
            'assigned_object_type': self.content_type,
            'assigned_object_id': self.zabbixserver.pk,
        }

    def test_valid_macro_creation(self):
        macro = ZabbixMacro(**self.valid_data)
        macro.full_clean()
        macro.save()
        self.assertEqual(ZabbixMacro.objects.count(), 1)
        self.assertEqual(macro.macro, '{$TEST_MACRO}')

    def test_macro_formatting_on_save(self):
        data = self.valid_data.copy()
        data['macro'] = 'MACRO_NAME'
        macro = ZabbixMacro(**data)
        macro.save()
        self.assertEqual(macro.macro, '{$MACRO_NAME}')

    def test_missing_assigned_object_raises_validation(self):
        data = self.valid_data.copy()
        data['assigned_object_type'] = None
        data['assigned_object_id'] = None
        macro = ZabbixMacro(**data)
        with self.assertRaises(ValidationError) as cm:
            macro.full_clean()
        self.assertIn('An assigned object must be provided', str(cm.exception))

    def test_macro_uniqueness_per_object(self):
        data1 = self.valid_data.copy()
        data1['macro'] = '{$DUPLICATE_MACRO}'
        data1['hostmacroid'] = 123

        ZabbixMacro.objects.create(**data1)

        data2 = self.valid_data.copy()
        data2['macro'] = '{$DUPLICATE_MACRO}'
        data2['hostmacroid'] = 999

        duplicate = ZabbixMacro(**data2)

        with self.assertRaises(ValidationError) as cm:
            duplicate.full_clean()

        self.assertIn('Macro must be unique per Assigned Object', str(cm.exception))

    def test_hostmacroid_uniqueness_per_object(self):
        ZabbixMacro.objects.create(**self.valid_data)
        new_data = self.valid_data.copy()
        new_data['macro'] = 'DIFFERENT_MACRO'
        duplicate = ZabbixMacro(**new_data)
        with self.assertRaises(ValidationError) as cm:
            duplicate.full_clean()
        self.assertIn('Host Macro ID must be unique per Assigned Object', str(cm.exception))

    def test_str_method_with_assigned_object(self):
        macro = ZabbixMacro.objects.create(**self.valid_data)
        self.assertEqual(str(macro), f'{{$TEST_MACRO}} ({self.zabbixserver.name})')

    def test_str_method_without_assigned_object(self):
        data = self.valid_data.copy()
        data['assigned_object_type'] = None
        data['assigned_object_id'] = None
        macro = ZabbixMacro(**data)
        macro.macro = '{$BARE_MACRO}'
        macro.full_clean = lambda: None
        self.assertEqual(str(macro), '{$BARE_MACRO}')
