from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from jinja2 import TemplateError, TemplateSyntaxError, UndefinedError

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.models import ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixServer, ZabbixConfigurationGroup


class ZabbixHostgroupAssignmentTestCase(TestCase):
    def setUp(self):
        self.device = create_test_device(name='Hostgroup Test Device')
        self.device_ct = ContentType.objects.get_for_model(Device)
        self.zabbixserver = ZabbixServer.objects.create(name='Zabbix Server 1')
        self.group = ZabbixHostgroup.objects.create(name='Group A', value='Static content', zabbixserver=self.zabbixserver)

    def test_valid_assignment(self):
        assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.group, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        self.assertEqual(str(assignment), f'{self.group.name} - {self.device.name}')

    def test_clean_fails_without_object(self):
        assignment = ZabbixHostgroupAssignment(zabbixhostgroup=self.group)
        with self.assertRaises(ValidationError) as cm:
            assignment.clean()
        self.assertIn('An assigned object must be provided', str(cm.exception))

    def test_unique_constraint(self):
        ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.group, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)

        duplicate = ZabbixHostgroupAssignment(zabbixhostgroup=self.group, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                duplicate.save()

    def test_is_template_false(self):
        assignment = ZabbixHostgroupAssignment(zabbixhostgroup=self.group, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        self.assertFalse(assignment.is_template())

    def test_is_template_true(self):
        self.group.value = 'Hello {{ object.name }}'
        self.group.save()

        assignment = ZabbixHostgroupAssignment(zabbixhostgroup=self.group, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        self.assertTrue(assignment.is_template())

    def test_render_success(self):
        self.group.value = 'Hello {{ object.name }}'
        self.group.save()
        assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.group, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        rendered, success = assignment.render()
        self.assertTrue(success)
        self.assertIn(self.device.name, rendered)

    def test_render_template_syntax_error(self):
        self.group.value = '{% broken syntax'
        self.group.save()
        assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.group, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        with patch('nbxsync.models.zabbixhostgroupassignment.render_jinja2', side_effect=TemplateSyntaxError('oops', lineno=1)):
            rendered, success = assignment.render()
            self.assertFalse(success)
            self.assertIn('Template syntax error', rendered)
            self.assertIn(self.group.value, rendered)
            self.assertIn('oops', rendered)

    def test_render_undefined_error(self):
        self.group.value = '{{ not_defined }}'
        self.group.save()
        assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.group, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        with patch('nbxsync.models.zabbixhostgroupassignment.render_jinja2', side_effect=UndefinedError('oops')):
            rendered, success = assignment.render()
            self.assertFalse(success)

    def test_render_template_error(self):
        self.group.value = '{{ some_error }}'
        self.group.save()
        assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.group, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        with patch('nbxsync.models.zabbixhostgroupassignment.render_jinja2', side_effect=TemplateError('boom')):
            rendered, success = assignment.render()
            self.assertFalse(success)

    def test_get_context_keys(self):
        assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.group, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        context = assignment.get_context()
        self.assertIn('object', context)
        self.assertIn('value', context)
        self.assertIn('name', context)

    def test_render_unexpected_exception(self):
        self.group.value = '{{ object.name }}'
        self.group.save()

        assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.group, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)

        with patch('nbxsync.models.zabbixhostgroupassignment.render_jinja2', side_effect=RuntimeError('unexpected error')):
            rendered, success = assignment.render()
            self.assertFalse(success)
            self.assertIn('Unexpected error rendering template', rendered)
            self.assertIn(self.group.value, rendered)
            self.assertIn('unexpected error', rendered)

    def test_render_with_configuration_group_returns_value_without_template_rendering(self):
        self.group.value = 'Hello {{ object.name }}'
        self.group.save()

        config_group = ZabbixConfigurationGroup()

        assignment = ZabbixHostgroupAssignment(zabbixhostgroup=self.group)
        assignment.assigned_object = config_group

        with patch('nbxsync.models.zabbixhostgroupassignment.render_jinja2') as mock_render:
            rendered, success = assignment.render()

        self.assertTrue(success)
        self.assertEqual(rendered, self.group.value)
        mock_render.assert_not_called()
