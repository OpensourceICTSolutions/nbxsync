from unittest.mock import MagicMock

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from ipam.models import IPAddress

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.choices import (
    ZabbixHostInterfaceTypeChoices,
    ZabbixInterfaceSNMPV3AuthProtoChoices,
    ZabbixInterfaceSNMPV3PrivProtoChoices,
    ZabbixInterfaceSNMPV3SecurityLevelChoices,
    ZabbixInterfaceTypeChoices,
    ZabbixInterfaceUseChoices,
)
from nbxsync.models import ZabbixHostInterface, ZabbixServer, ZabbixServerAssignment
from nbxsync.utils.sync.hostinterfacesync import HostInterfaceSync


class HostInterfaceSyncTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.zabbixserver = ZabbixServer.objects.create(name='Zabbix Server 1', url='http://example.com', token='dummy-token')

        cls.device = create_test_device(name='HG Sync TestDev1')
        cls.device_ct = ContentType.objects.get_for_model(Device)

        cls.ip = IPAddress.objects.create(address='10.1.1.1/32')

        cls.hostinterface = ZabbixHostInterface.objects.create(
            zabbixserver=cls.zabbixserver, type=ZabbixHostInterfaceTypeChoices.AGENT, interface_type=ZabbixInterfaceTypeChoices.DEFAULT, useip=ZabbixInterfaceUseChoices.IP, dns='router1.local', ip=cls.ip, port=10050, assigned_object_type=cls.device_ct, assigned_object_id=cls.device.id
        )

        cls.assignment = ZabbixServerAssignment.objects.create(zabbixserver=cls.zabbixserver, hostid='10101', assigned_object_type=cls.device_ct, assigned_object_id=cls.device.id)

    def test_get_create_params_basic(self):
        sync = HostInterfaceSync(api=None, netbox_obj=self.hostinterface)
        sync.context = {}

        params = sync.get_create_params()

        self.assertEqual(params['hostid'], 10101)
        self.assertEqual(params['ip'], '10.1.1.1')
        self.assertEqual(params['dns'], 'router1.local')
        self.assertEqual(params['port'], '10050')
        self.assertEqual(params['useip'], ZabbixInterfaceUseChoices.IP)
        self.assertEqual(params['main'], ZabbixInterfaceTypeChoices.DEFAULT)

    def test_get_create_params_with_snmpv2(self):
        self.hostinterface.type = 2
        self.hostinterface.snmp_version = 2
        self.hostinterface.snmp_usebulk = True
        self.hostinterface.save()

        sync = HostInterfaceSync(api=None, netbox_obj=self.hostinterface)
        sync.context = {'hostid': '12345'}
        sync.pluginsettings = type('plugin', (), {})()
        sync.pluginsettings.snmpconfig = type('snmpconfig', (), {'snmp_community': '{$SNMP_COMMUNITY}'})()

        params = sync.get_create_params()
        snmp = params['details']

        self.assertEqual(snmp['version'], 2)
        self.assertEqual(snmp['bulk'], 1)
        self.assertEqual(snmp['community'], '{$SNMP_COMMUNITY}')

    def test_get_create_params_with_snmpv3(self):
        self.hostinterface.type = 2
        self.hostinterface.snmp_version = 3
        self.hostinterface.snmp_usebulk = False
        self.hostinterface.snmpv3_context_name = 'ctx'
        self.hostinterface.snmpv3_security_name = 'sec'
        self.hostinterface.snmpv3_security_level = ZabbixInterfaceSNMPV3SecurityLevelChoices.AUTHNOPRIV
        self.hostinterface.snmpv3_authentication_protocol = ZabbixInterfaceSNMPV3AuthProtoChoices.SHA1
        self.hostinterface.snmpv3_privacy_protocol = ZabbixInterfaceSNMPV3PrivProtoChoices.AES256
        self.hostinterface.save()

        sync = HostInterfaceSync(api=None, netbox_obj=self.hostinterface)
        sync.context = {'hostid': '12345'}
        sync.pluginsettings = type('plugin', (), {})()
        sync.pluginsettings.snmpconfig = type('snmpconfig', (), {'snmp_authpass': '{$SNMPV3_AUTHPASS}', 'snmp_privpass': '{$SNMPV3_PRIVPASS}'})()

        params = sync.get_create_params()
        snmp = params['details']

        self.assertEqual(snmp['version'], 3)
        self.assertEqual(snmp['bulk'], 0)
        self.assertEqual(snmp['contextname'], 'ctx')
        self.assertEqual(snmp['securityname'], 'sec')
        self.assertEqual(snmp['securitylevel'], ZabbixInterfaceSNMPV3SecurityLevelChoices.AUTHNOPRIV)
        self.assertEqual(snmp['authprotocol'], ZabbixInterfaceSNMPV3AuthProtoChoices.SHA1)
        self.assertEqual(snmp['privprotocol'], ZabbixInterfaceSNMPV3PrivProtoChoices.AES256)
        self.assertEqual(snmp['authpassphrase'], '{$SNMPV3_AUTHPASS}')
        self.assertEqual(snmp['privpassphrase'], '{$SNMPV3_PRIVPASS}')

    def test_get_update_params_adds_interfaceid(self):
        self.hostinterface.interfaceid = 222
        self.hostinterface.save()
        sync = HostInterfaceSync(api=None, netbox_obj=self.hostinterface)
        sync.context = {'hostid': '10101'}

        params = sync.get_update_params()
        self.assertEqual(params['interfaceid'], 222)

    def test_sync_from_zabbix_sets_fields(self):
        data = {
            'interfaceid': 123,
            'type': 2,
            'useip': 1,
            'main': 1,
            'dns': 'router1.sync',
            'port': '161',
            'ip': '10.1.1.1',
            'details': {'version': 2, 'bulk': 1, 'community': 'public'},
        }

        sync = HostInterfaceSync(api=None, netbox_obj=self.hostinterface)
        sync.sync_from_zabbix(data)

        updated = ZabbixHostInterface.objects.get(pk=self.hostinterface.pk)
        self.assertEqual(updated.interfaceid, 123)
        self.assertEqual(updated.type, 2)
        self.assertEqual(updated.useip, 1)
        self.assertEqual(updated.interface_type, 1)
        self.assertEqual(updated.dns, 'router1.sync')
        self.assertEqual(updated.port, 161)
        self.assertEqual(updated.snmp_version, 2)
        self.assertTrue(updated.snmp_usebulk)
        self.assertEqual(updated.snmp_community, 'public')

    def test_api_object_and_result_key(self):
        mock_api = MagicMock()
        sync = HostInterfaceSync(api=mock_api, netbox_obj=self.hostinterface)
        self.assertEqual(sync.api_object(), mock_api.hostinterface)
        self.assertEqual(sync.result_key(), 'interfaceids')

    def test_get_name_value_returns_device_name(self):
        sync = HostInterfaceSync(api=MagicMock(), netbox_obj=self.hostinterface)
        expected_name = self.device.name

        result = sync.get_name_value()
        self.assertEqual(result, expected_name)

    def test_get_create_params_returns_empty_when_no_assignment(self):
        # Remove the assignment to simulate a missing one
        ZabbixServerAssignment.objects.all().delete()

        sync = HostInterfaceSync(api=None, netbox_obj=self.hostinterface)
        sync.context = {}

        params = sync.get_create_params()
        self.assertEqual(params, {})

    def test_sync_from_zabbix_sets_snmpv3_fields(self):
        data = {
            'interfaceid': '124',
            'type': 2,
            'useip': 1,
            'main': 1,
            'dns': 'router1.snmpv3',
            'port': '161',
            'ip': '10.1.1.1',
            'details': {
                'version': 3,
                'bulk': 0,
                'contextname': 'ctxv3',
                'securityname': 'secv3',
                'securitylevel': ZabbixInterfaceSNMPV3SecurityLevelChoices.AUTHPRIV,
                'authprotocol': ZabbixInterfaceSNMPV3AuthProtoChoices.SHA256,
                'privprotocol': ZabbixInterfaceSNMPV3PrivProtoChoices.AES192,
            },
        }

        # Update the interface to type=SNMP to trigger the SNMP branch
        self.hostinterface.type = 2
        self.hostinterface.snmp_version = 3
        self.hostinterface.save()

        sync = HostInterfaceSync(api=None, netbox_obj=self.hostinterface)
        sync.sync_from_zabbix(data)

        updated = ZabbixHostInterface.objects.get(pk=self.hostinterface.pk)
        self.assertEqual(updated.interfaceid, 124)
        self.assertEqual(updated.snmpv3_context_name, 'ctxv3')
        self.assertEqual(updated.snmpv3_security_name, 'secv3')
        self.assertEqual(updated.snmpv3_security_level, ZabbixInterfaceSNMPV3SecurityLevelChoices.AUTHPRIV)
        self.assertEqual(updated.snmpv3_authentication_protocol, ZabbixInterfaceSNMPV3AuthProtoChoices.SHA256)
        self.assertEqual(updated.snmpv3_privacy_protocol, ZabbixInterfaceSNMPV3PrivProtoChoices.AES192)

    def test_sync_from_zabbix_handles_exception_and_calls_update_sync_info(self):
        data = {
            'interfaceid': 'bad-int',  # triggers ValueError when casting to int
            'type': 2,
            'useip': 1,
            'main': 1,
            'dns': 'router1.invalid',
            'port': '161',
            'ip': '10.1.1.1',
            'details': {'version': 2, 'bulk': 1, 'community': 'public'},
        }

        self.hostinterface.update_sync_info = MagicMock()

        sync = HostInterfaceSync(api=None, netbox_obj=self.hostinterface)
        sync.sync_from_zabbix(data)

        self.hostinterface.update_sync_info.assert_called_once()
        args, kwargs = self.hostinterface.update_sync_info.call_args
        assert kwargs.get('success') is False
        assert 'invalid literal' in kwargs.get('message')  # message from ValueError
