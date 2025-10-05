from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase
from django.urls import reverse
from ipam.models import IPAddress

from dcim.models import Device
from utilities.testing import create_test_device, create_test_user

from nbxsync.models import ZabbixHostInterface, ZabbixHostInventory, ZabbixServer, ZabbixServerAssignment
from nbxsync.tables import ZabbixHostInterfaceObjectViewTable, ZabbixServerAssignmentObjectViewTable
from nbxsync.views import ZabbixDeviceTabView


class ZabbixDeviceTabViewTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.device = create_test_device(name='TestDevice')

        self.user = create_test_user()
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)

        url = f'{reverse("dcim:device", args=[self.device.pk])}/zabbix/'
        self.request = self.factory.get(url)
        self.request.user = self.user

        self.response = self.client.get(url)

        # Create ContentType for device
        device_ct = ContentType.objects.get_for_model(Device)

        # Create dummy related objects
        self.zabbixserver = ZabbixServer.objects.create(
            name='Zabbix Server A',
            description='Test Server',
            url='http://example.com',
            token='dummy-token',
            validate_certs=True,
        )
        self.ipaddress = IPAddress.objects.create(address='1.1.1.1/32')
        self.hostinterface = ZabbixHostInterface.objects.create(
            zabbixserver=self.zabbixserver,
            type=1,
            useip=1,
            interface_type=1,
            ip=self.ipaddress,
            port=10051,
            assigned_object_type=device_ct,
            assigned_object_id=self.device.id,
        )
        self.zabbixassignment = ZabbixServerAssignment.objects.create(zabbixserver=self.zabbixserver, assigned_object_type=device_ct, assigned_object_id=self.device.id)
        self.hostinventory = ZabbixHostInventory.objects.create(alias='Demo', assigned_object_type=device_ct, assigned_object_id=self.device.id)

    def test_get_extra_context(self):
        view = ZabbixDeviceTabView()
        view.request = self.request
        view.kwargs = {'pk': self.device.pk}
        view.object = self.device

        context = view.get_extra_context(self.request, self.device)

        # Test that the tables and assignment are in context
        self.assertIn('hostinterface_assignment_table', context)
        self.assertIsInstance(context['hostinterface_assignment_table'], ZabbixHostInterfaceObjectViewTable)

        self.assertIn('zabbixserver_assignments_table', context)
        self.assertIsInstance(context['zabbixserver_assignments_table'], ZabbixServerAssignmentObjectViewTable)

        self.assertIn('hostinventory_assignment', context)
        self.assertEqual(context['hostinventory_assignment'], self.hostinventory)

    def test_get_extra_context_empty(self):
        # Clear created objects
        ZabbixHostInterface.objects.all().delete()
        ZabbixServerAssignment.objects.all().delete()
        ZabbixHostInventory.objects.all().delete()

        view = ZabbixDeviceTabView()
        view.request = self.request
        view.kwargs = {'pk': self.device.pk}
        view.object = self.device

        context = view.get_extra_context(self.request, self.device)

        self.assertIsNone(context['hostinterface_assignment_table'])
        self.assertIsNone(context['zabbixserver_assignments_table'])
        self.assertIsNone(context['hostinventory_assignment'])
