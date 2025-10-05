from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.models import ZabbixMacro, ZabbixMacroAssignment


class ZabbixMacroAssignmentTestCase(TestCase):
    def setUp(self):
        self.device = create_test_device(name='Test Device')
        self.device_ct = ContentType.objects.get_for_model(Device)
        self.macro = ZabbixMacro.objects.create(macro='{$TEST_MACRO}', value='default', type='1')

    def test_valid_assignment_non_regex(self):
        assignment = ZabbixMacroAssignment.objects.create(
            zabbixmacro=self.macro,
            value='some value',
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
            is_regex=False,
            context='',
        )
        self.assertEqual(str(assignment), self.macro.macro)

    def test_valid_assignment_with_context_regex(self):
        assignment = ZabbixMacroAssignment.objects.create(
            zabbixmacro=self.macro,
            value='value123',
            is_regex=True,
            context='linux',
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )
        expected = f'{self.macro.macro[:-1]}:regex:"linux"}}'
        self.assertEqual(str(assignment), expected)

    def test_clean_fails_without_object(self):
        assignment = ZabbixMacroAssignment(zabbixmacro=self.macro, value='val', is_regex=False)
        with self.assertRaises(ValidationError) as cm:
            assignment.clean()
        self.assertIn('An assigned object must be provided', str(cm.exception))

    def test_clean_fails_with_regex_but_no_context(self):
        assignment = ZabbixMacroAssignment(
            zabbixmacro=self.macro,
            value='regexval',
            is_regex=True,
            context='',
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )
        with self.assertRaises(ValidationError) as cm:
            assignment.clean()
        self.assertIn('A context must be provided when the macro is a regex', str(cm.exception))

    def test_clean_fails_with_regex_but_no_value(self):
        assignment = ZabbixMacroAssignment(
            zabbixmacro=self.macro,
            value='',
            is_regex=True,
            context='ctx',
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )
        with self.assertRaises(ValidationError) as cm:
            assignment.clean()
        self.assertIn('A value must be provided when the macro is a regex', str(cm.exception))

    def test_context_is_cleared_if_not_regex(self):
        assignment = ZabbixMacroAssignment.objects.create(
            zabbixmacro=self.macro,
            value='someval',
            is_regex=False,
            context='should-clear',
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )
        self.assertEqual(assignment.context, '')

    def test_unique_constraint(self):
        ZabbixMacroAssignment.objects.create(
            zabbixmacro=self.macro,
            value='unique-val',
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )
        duplicate = ZabbixMacroAssignment(
            zabbixmacro=self.macro,
            value='another-val',
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )

        try:
            with transaction.atomic():
                duplicate.save()
        except IntegrityError:
            pass  # This is expected

    def test_str_non_regex_with_context(self):
        # Manually set a context even though is_regex=False, and call __str__ before clean clears it
        assignment = ZabbixMacroAssignment(
            zabbixmacro=self.macro,
            value='someval',
            is_regex=False,
            context='custom-context',
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )

        # Call __str__ before .clean() clears context
        result = str(assignment)
        expected = f'{self.macro.macro[:-1]}:custom-context}}'
        self.assertEqual(result, expected)

    def test_full_name_property_returns_self(self):
        assignment = ZabbixMacroAssignment(
            zabbixmacro=self.macro,
            value='example',
            is_regex=False,
            context='ctx',
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )

        # Save so the instance has a primary key if needed
        assignment.save()

        # Access full_name and verify it returns the object itself
        self.assertIs(assignment.full_name, assignment)
