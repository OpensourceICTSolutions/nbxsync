from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from ipam.models import IPAddress

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.choices import (
    ZabbixHostInterfaceSNMPVersionChoices,
    ZabbixHostInterfaceTypeChoices,
    ZabbixInterfaceUseChoices,
    ZabbixTLSChoices,
)
from nbxsync.models import ZabbixHostInterface, ZabbixServer


class ZabbixHostInterfaceTestCase(TestCase):
    def setUp(self):
        self.device = create_test_device(name='HostInterfaceDevice')
        self.device_ct = ContentType.objects.get_for_model(Device)
        self.zabbixserver = ZabbixServer.objects.create(name='Zabbix Main')
        self.ip = IPAddress.objects.create(address='10.0.0.1/32')

    def test_valid_ip_interface(self):
        iface = ZabbixHostInterface.objects.create(
            zabbixserver=self.zabbixserver,
            type=ZabbixHostInterfaceTypeChoices.AGENT,
            useip=ZabbixInterfaceUseChoices.IP,
            ip=self.ip,
            port=10050,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )
        self.assertEqual(iface.get_useip_display(), 'IP')
        self.assertEqual(iface.get_type_display(), 'Agent')
        self.assertIn(str(self.device), str(iface))  # __str__

    def test_valid_dns_interface(self):
        iface = ZabbixHostInterface(
            zabbixserver=self.zabbixserver,
            type=ZabbixHostInterfaceTypeChoices.JMX,
            useip=ZabbixInterfaceUseChoices.DNS,
            dns='host.example.com',
            port=1234,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )
        iface.full_clean()  # Calls .clean()
        self.assertEqual(iface.dns, 'host.example.com')

    def test_clean_fails_without_object(self):
        iface = ZabbixHostInterface(
            zabbixserver=self.zabbixserver,
            type=ZabbixHostInterfaceTypeChoices.AGENT,
            useip=ZabbixInterfaceUseChoices.IP,
            ip=self.ip,
            port=10050,
        )
        with self.assertRaises(ValidationError) as cm:
            iface.clean()
        self.assertIn('An assigned object must be provided', str(cm.exception))

    def test_clean_fails_missing_ip(self):
        iface = ZabbixHostInterface(
            zabbixserver=self.zabbixserver,
            type=ZabbixHostInterfaceTypeChoices.AGENT,
            useip=ZabbixInterfaceUseChoices.IP,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )
        with self.assertRaises(ValidationError) as cm:
            iface.clean()
        self.assertIn('ip', cm.exception.message_dict)

    def test_clean_fails_missing_dns(self):
        iface = ZabbixHostInterface(
            zabbixserver=self.zabbixserver,
            type=ZabbixHostInterfaceTypeChoices.AGENT,
            useip=ZabbixInterfaceUseChoices.DNS,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )
        with self.assertRaises(ValidationError) as cm:
            iface.clean()
        self.assertIn('dns', cm.exception.message_dict)

    def test_clean_fails_invalid_tls_psk(self):
        iface = ZabbixHostInterface(
            zabbixserver=self.zabbixserver,
            type=ZabbixHostInterfaceTypeChoices.AGENT,
            useip=ZabbixInterfaceUseChoices.IP,
            ip=self.ip,
            port=10050,
            tls_connect=ZabbixTLSChoices.PSK,
            tls_psk='short',
            tls_psk_identity='',
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )
        with self.assertRaises(ValidationError) as cm:
            iface.clean()
        self.assertIn('tls_psk', cm.exception.message_dict)
        self.assertIn('tls_psk_identity', cm.exception.message_dict)

    def test_clean_fails_snmpv3_min_passphrase_length(self):
        iface = ZabbixHostInterface(
            zabbixserver=self.zabbixserver,
            type=ZabbixHostInterfaceTypeChoices.SNMP,
            snmp_version=ZabbixHostInterfaceSNMPVersionChoices.SNMPV3,
            snmpv3_security_name='',
            snmpv3_authentication_passphrase='short',
            snmpv3_privacy_passphrase='short',
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )
        with self.assertRaises(ValidationError) as cm:
            iface.clean()
        self.assertIn('snmpv3_security_name', cm.exception.message_dict)
        self.assertIn('snmpv3_authentication_passphrase', cm.exception.message_dict)
        self.assertIn('snmpv3_privacy_passphrase', cm.exception.message_dict)

    def test_unique_constraint(self):
        ZabbixHostInterface.objects.create(
            zabbixserver=self.zabbixserver,
            type=ZabbixHostInterfaceTypeChoices.AGENT,
            useip=ZabbixInterfaceUseChoices.IP,
            ip=self.ip,
            port=10050,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )

        duplicate = ZabbixHostInterface(
            zabbixserver=self.zabbixserver,
            type=ZabbixHostInterfaceTypeChoices.AGENT,
            useip=ZabbixInterfaceUseChoices.IP,
            ip=self.ip,
            port=10050,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                duplicate.save()

    def test_get_display_methods(self):
        iface = ZabbixHostInterface(
            zabbixserver=self.zabbixserver,
            useip=ZabbixInterfaceUseChoices.IP,
            type=ZabbixHostInterfaceTypeChoices.AGENT,
            tls_connect=ZabbixTLSChoices.CERT,
            tls_accept=[ZabbixTLSChoices.NO_ENCRYPTION, ZabbixTLSChoices.PSK],
            ipmi_privilege=4,
            ipmi_authtype=2,
            snmp_version=3,
            snmpv3_security_level=2,
            snmpv3_authentication_protocol=1,
            snmpv3_privacy_protocol=0,
        )
        self.assertEqual(iface.get_useip_display(), 'IP')
        self.assertEqual(iface.get_type_display(), 'Agent')
        self.assertEqual(iface.get_tls_connect_display(), 'Certificate')
        self.assertEqual(iface.get_tls_accept_display(), ['No Encryption', 'Pre-Shared key'])
        self.assertEqual(iface.get_ipmi_privlege_display(), 'Admin')
        self.assertEqual(iface.get_ipmi_authtype_display(), 'MD5')
        self.assertEqual(iface.get_snmp_version_display(), 'SNMPv3')
        self.assertEqual(iface.get_snmpv3_security_level_display(), 'authPriv')
        self.assertEqual(iface.get_snmpv3_authentication_protocol_display(), 'SHA1')
        self.assertEqual(iface.get_snmpv3_snmpv3_privacy_protocol_display(), 'DES')

    def test_clean_fails_without_zabbixserver(self):
        iface = ZabbixHostInterface(
            type=ZabbixHostInterfaceTypeChoices.AGENT,
            useip=ZabbixInterfaceUseChoices.IP,
            ip=self.ip,
            port=10050,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )
        with self.assertRaises(ValidationError) as cm:
            iface.clean()
        self.assertIn('zabbixserver', cm.exception.message_dict)
        self.assertIn('A hostinterface must always be assigned to a Zabbix Server', cm.exception.message_dict['zabbixserver'])

    def test_clean_fails_with_invalid_tls_psk(self):
        iface = ZabbixHostInterface(
            zabbixserver=self.zabbixserver,
            type=ZabbixHostInterfaceTypeChoices.AGENT,
            useip=ZabbixInterfaceUseChoices.IP,
            ip=self.ip,
            port=10050,
            tls_connect=ZabbixTLSChoices.PSK,
            tls_psk='this_is_invalidthis_is_invalidthis_',  # invalid: not hex
            tls_psk_identity='identity',
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
        )

        with self.assertRaises(ValidationError) as cm:
            iface.clean()
        self.assertIn('tls_psk', cm.exception.message_dict)
        self.assertIn('TLS PSK must contain only hexadecimal characters', cm.exception.message_dict['tls_psk'][0])
