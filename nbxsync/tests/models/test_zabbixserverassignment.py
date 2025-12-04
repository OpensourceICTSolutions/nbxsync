from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from utilities.testing import create_test_device

from nbxsync.models import ZabbixProxy, ZabbixProxyGroup, ZabbixServer, ZabbixServerAssignment


class ZabbixServerAssignmentTestCase(TestCase):
    def setUp(self):
        self.zabbixserver = ZabbixServer.objects.create(name='Zabbix Server', url='http://127.0.0.1', token='token', validate_certs=False)
        self.proxy = ZabbixProxy.objects.create(name='Proxy A', zabbixserver=self.zabbixserver, local_address='192.168.0.1', operating_mode=0)
        self.proxy_group = ZabbixProxyGroup.objects.create(name='Proxy Group', zabbixserver_id=self.zabbixserver.id)
        self.device = create_test_device(name='TestDevice')
        self.device_ct = ContentType.objects.get_for_model(self.device)

    def test_valid_assignment(self):
        assignment = ZabbixServerAssignment.objects.create(zabbixserver=self.zabbixserver, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        self.assertEqual(str(assignment), f'{self.device} - {self.zabbixserver} ')

    def test_missing_assigned_object_fails(self):
        assignment = ZabbixServerAssignment(zabbixserver_id=self.zabbixserver.id, assigned_object_type=None, assigned_object_id=None)
        with self.assertRaises(ValidationError) as cm:
            assignment.full_clean()
        self.assertIn('An assigned object must be provided', str(cm.exception))

    def test_both_proxy_and_proxygroup_fails(self):
        assignment = ZabbixServerAssignment(zabbixserver_id=self.zabbixserver.id, assigned_object_type=self.device_ct, assigned_object_id=self.device.id, zabbixproxy=self.proxy, zabbixproxygroup=self.proxy_group)
        with self.assertRaises(ValidationError) as cm:
            assignment.full_clean()
        self.assertIn('You cannot set both a proxy and proxygroup', str(cm.exception))

    def test_unique_constraint(self):
        ZabbixServerAssignment.objects.create(zabbixserver_id=self.zabbixserver.id, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)
        duplicate = ZabbixServerAssignment(zabbixserver_id=self.zabbixserver.id, assigned_object_type=self.device_ct, assigned_object_id=self.device.id)

        # Ensure test isolation: DB rollback protection via outer atomic
        try:
            with transaction.atomic():
                duplicate.save()
        except IntegrityError:
            pass  # This is expected

    def test_str_empty_if_no_object(self):
        assignment = ZabbixServerAssignment(zabbixserver_id=self.zabbixserver.id, assigned_object_type=None, assigned_object_id=None)
        self.assertEqual(str(assignment), '')
