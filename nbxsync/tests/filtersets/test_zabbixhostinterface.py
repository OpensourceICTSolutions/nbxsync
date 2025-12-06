from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from ipam.models import IPAddress

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.filtersets import ZabbixHostInterfaceFilterSet
from nbxsync.models import ZabbixHostInterface, ZabbixServer


class ZabbixHostInterfaceFilterSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.servers = [
            ZabbixServer.objects.create(name='Server A', url='http://a.example.com', token='token-a', validate_certs=True),
            ZabbixServer.objects.create(name='Server B', url='http://b.example.com', token='token-b', validate_certs=True),
        ]

        cls.devices = [create_test_device(name='Device 1'), create_test_device(name='Device 2')]
        cls.device_ct = ContentType.objects.get_for_model(Device)

        cls.ips = [IPAddress.objects.create(address='192.0.2.1/32'), IPAddress.objects.create(address='192.0.2.2/32')]

        cls.interfaces = [
            ZabbixHostInterface.objects.create(
                zabbixserver=cls.servers[0],
                type=1,
                interface_type=1,
                useip=1,
                dns='agent1.example.com',
                ip=cls.ips[0],
                port=10050,
                snmp_community='public',
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[0].id,
            ),
            ZabbixHostInterface.objects.create(
                zabbixserver=cls.servers[1],
                type=2,
                interface_type=2,
                useip=0,
                dns='snmp1.example.com',
                ip=cls.ips[1],
                port=161,
                snmp_community='secret',
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[1].id,
            ),
        ]

    def test_search_by_zabbixserver_name(self):
        f = ZabbixHostInterfaceFilterSet({'q': 'Server A'}, queryset=ZabbixHostInterface.objects.all())
        self.assertIn(self.interfaces[0], f.qs)
        self.assertNotIn(self.interfaces[1], f.qs)

    def test_search_by_dns(self):
        f = ZabbixHostInterfaceFilterSet({'q': 'agent1'}, queryset=ZabbixHostInterface.objects.all())
        self.assertIn(self.interfaces[0], f.qs)

    def test_blank_search_returns_all(self):
        queryset = ZabbixHostInterface.objects.all()
        f = ZabbixHostInterfaceFilterSet({'q': '  '}, queryset=queryset)
        self.assertQuerySetEqual(f.qs.order_by('pk'), queryset.order_by('pk'), transform=lambda x: x)

    def test_filter_by_dns_field(self):
        f = ZabbixHostInterfaceFilterSet({'dns': 'agent1'}, queryset=ZabbixHostInterface.objects.all())
        self.assertIn(self.interfaces[0], f.qs)

    def test_filter_by_port(self):
        f = ZabbixHostInterfaceFilterSet({'port': '161'}, queryset=ZabbixHostInterface.objects.all())
        self.assertIn(self.interfaces[1], f.qs)

    def test_filter_by_snmp_community(self):
        f = ZabbixHostInterfaceFilterSet({'snmp_community': 'secret'}, queryset=ZabbixHostInterface.objects.all())
        self.assertIn(self.interfaces[1], f.qs)

    def test_filter_by_type_and_interface_type(self):
        f = ZabbixHostInterfaceFilterSet({'type': 2, 'interface_type': 2}, queryset=ZabbixHostInterface.objects.all())
        self.assertIn(self.interfaces[1], f.qs)

    def test_search_method_directly_hits_return_queryset(self):
        queryset = ZabbixHostInterface.objects.all()
        f = ZabbixHostInterfaceFilterSet({}, queryset=queryset)
        result = f.search(queryset, name='q', value='   ')
        self.assertQuerySetEqual(result.order_by('pk'), queryset.order_by('pk'), transform=lambda x: x)

    def test_filter_by_assigned_object_type(self):
        f = ZabbixHostInterfaceFilterSet({'assigned_object_type': f'{self.device_ct.app_label}.{self.device_ct.model}'}, queryset=ZabbixHostInterface.objects.all())
        self.assertEqual(f.qs.count(), 2)

    def test_filter_fails_with_wrong_content_type(self):
        wrong_ct = ContentType.objects.get_for_model(ZabbixHostInterface)
        f = ZabbixHostInterfaceFilterSet(
            {'assigned_object_type': f'{wrong_ct.app_label}.{wrong_ct.model}', 'assigned_object_id': self.devices[0].id},
            queryset=ZabbixHostInterface.objects.all(),
        )
        self.assertEqual(f.qs.count(), 0)

    def test_filter_by_assigned_object_id_alone(self):
        f = ZabbixHostInterfaceFilterSet({'assigned_object_id': self.devices[0].id}, queryset=ZabbixHostInterface.objects.all())
        self.assertIn(self.interfaces[0], f.qs)
        self.assertNotIn(self.interfaces[1], f.qs)
