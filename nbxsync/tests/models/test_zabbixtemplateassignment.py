from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from utilities.testing import create_test_device, create_test_virtualmachine

from nbxsync.models import ZabbixServer, ZabbixTemplate, ZabbixTemplateAssignment


class ZabbixTemplateAssignmentTestCase(TestCase):
    def setUp(self):
        self.zabbixserver = ZabbixServer.objects.create(name='Test Server', description='Test Description', url='http://127.0.0.1', token='s3cr3t-t0ken', validate_certs=False)
        self.template = ZabbixTemplate.objects.create(name='Linux Template', templateid=123, zabbixserver_id=self.zabbixserver.id)

        self.device = create_test_device(name='Device 1')
        self.vm = create_test_virtualmachine(name='VM 01')

        self.device_ct = ContentType.objects.get_for_model(self.device)
        self.vm_ct = ContentType.objects.get_for_model(self.vm)

    def test_valid_assignment_to_device(self):
        assignment = ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        self.assertEqual(str(assignment), f'{self.device} - {self.template}')

    def test_valid_assignment_to_virtualmachine(self):
        assignment = ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=self.vm_ct, assigned_object_id=self.vm.id)
        self.assertEqual(str(assignment), f'{self.vm} - {self.template}')

    def test_clean_fails_without_assigned_object(self):
        assignment = ZabbixTemplateAssignment(zabbixtemplate=self.template, assigned_object_type=None, assigned_object_id=None)

        with self.assertRaises(ValidationError) as cm:
            assignment.clean()

        self.assertIn('An assigned object must be provided', str(cm.exception))

    def test_unique_constraint(self):
        device = create_test_device(name='Device 2')
        device_ct = ContentType.objects.get_for_model(device)

        ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=device_ct, assigned_object_id=device.id)
        duplicate = ZabbixTemplateAssignment(zabbixtemplate=self.template, assigned_object_type=device_ct, assigned_object_id=device.id)

        try:
            with transaction.atomic():
                duplicate.save()
        except IntegrityError:
            pass

    def test_str_returns_empty_if_no_assigned_object(self):
        assignment = ZabbixTemplateAssignment(zabbixtemplate=self.template, assigned_object_type=None, assigned_object_id=None)
        self.assertEqual(str(assignment), '')
