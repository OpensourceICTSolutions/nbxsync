from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from jinja2 import TemplateError, TemplateSyntaxError, UndefinedError

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.models import ZabbixTag, ZabbixTagAssignment


class ZabbixTagAssignmentTestCase(TestCase):
    def setUp(self):
        self.device = create_test_device(name='TaggedDevice')
        self.device_ct = ContentType.objects.get_for_model(Device)
        self.tag = ZabbixTag.objects.create(name='Environment', tag='env', value='{{ object.name }}')

    def test_valid_assignment_and_render(self):
        assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        rendered, success = assignment.render()
        self.assertTrue(success)
        self.assertEqual(rendered, self.device.name)

    def test_clean_fails_without_object(self):
        assignment = ZabbixTagAssignment(zabbixtag=self.tag)
        with self.assertRaises(ValidationError) as cm:
            assignment.clean()
        self.assertIn('An assigned object must be provided', str(cm.exception))

    def test_is_template_true(self):
        assignment = ZabbixTagAssignment(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        self.assertTrue(assignment.is_template())

    def test_is_template_false(self):
        static_tag = ZabbixTag.objects.create(name='Static', tag='static', value='not a template')
        assignment = ZabbixTagAssignment(zabbixtag=static_tag, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        self.assertFalse(assignment.is_template())

    def test_render_template_syntax_error(self):
        self.tag.value = '{% broken syntax'
        self.tag.save()
        assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        with patch('nbxsync.models.zabbixtagassignment.render_jinja2', side_effect=TemplateSyntaxError('oops', 1)):
            rendered, success = assignment.render()
            self.assertFalse(success)
            self.assertEqual(rendered, '')

    def test_render_undefined_error(self):
        assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        with patch('nbxsync.models.zabbixtagassignment.render_jinja2', side_effect=UndefinedError('undefined variable')):
            rendered, success = assignment.render()
            self.assertFalse(success)
            self.assertEqual(rendered, '')

    def test_render_template_error(self):
        assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        with patch('nbxsync.models.zabbixtagassignment.render_jinja2', side_effect=TemplateError('render fail')):
            rendered, success = assignment.render()
            self.assertFalse(success)
            self.assertEqual(rendered, '')

    def test_render_generic_exception(self):
        assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        with patch('nbxsync.models.zabbixtagassignment.render_jinja2', side_effect=Exception('boom')):
            rendered, success = assignment.render()
            self.assertFalse(success)
            self.assertEqual(rendered, '')

    def test_unique_constraint(self):
        ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        duplicate = ZabbixTagAssignment(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                duplicate.save()

    def test_get_context_values(self):
        assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        context = assignment.get_context(extra='extra_val')
        self.assertEqual(context['object'], self.device)
        self.assertEqual(context['tag'], self.tag.tag)
        self.assertEqual(context['value'], self.tag.value)
        self.assertEqual(context['name'], self.tag.name)
        self.assertEqual(context['description'], self.tag.description)
        self.assertEqual(context['extra'], 'extra_val')

    def test_str_method(self):
        assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        expected = f'{self.tag.name} - {self.device.name}'
        self.assertEqual(str(assignment), expected)
