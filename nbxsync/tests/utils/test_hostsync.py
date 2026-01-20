from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from ipam.models import IPAddress

from dcim.models import Device
from utilities.testing import create_test_device, create_test_virtualmachine

from nbxsync.choices import *
from nbxsync.choices.syncsot import SyncSOT
from nbxsync.choices.zabbixstatus import ZabbixHostStatus
from nbxsync.models import ZabbixHostInterface, ZabbixProxy, ZabbixProxyGroup, ZabbixServer
from nbxsync.utils.sync import HostSync


class HostSyncTestCase(TestCase):
    def setUp(self):
        # Setup NetBox objects
        self.device = create_test_device(name='Test Device')
        self.vm = create_test_virtualmachine(name='Test VM1')

        self.device_ct = ContentType.objects.get_for_model(Device)

        self.zabbixserver = ZabbixServer.objects.create(name='Zabbix Server A', description='Test Server', url='http://example.com', token='dummy-token', validate_certs=True)
        self.proxygroup = ZabbixProxyGroup.objects.create(name='Proxy Group A', zabbixserver=self.zabbixserver, proxy_groupid=456)

        self.zabbix_proxy = ZabbixProxy.objects.create(
            name='Active Proxy #1',
            zabbixserver=self.zabbixserver,
            proxygroup=self.proxygroup,
            operating_mode=ZabbixProxyTypeChoices.ACTIVE,
            local_address='192.168.1.1',
            local_port=10051,
            allowed_addresses=['10.0.0.1'],
            tls_accept=[ZabbixTLSChoices.PSK],
            tls_psk_identity='psk-id',
            tls_psk='2AB09AD2496109A3BFAC0C6BB4D37CEF',
        )
        self.ip = IPAddress.objects.create(address='192.0.2.1/24')

        # AGENT interface
        self.interface_agent = ZabbixHostInterface.objects.create(
            assigned_object_type=self.device_ct, assigned_object_id=self.device.id, zabbixserver=self.zabbixserver, type=ZabbixHostInterfaceTypeChoices.AGENT, interfaceid=10001, ip=self.ip, port=161, tls_connect=1, tls_accept=[1], tls_psk_identity='psk_id', tls_psk='psk_secret'
        )

        # SNMPv2 interface
        self.interface_snmp = ZabbixHostInterface.objects.create(
            assigned_object_type=self.device_ct, assigned_object_id=self.device.id, zabbixserver=self.zabbixserver, type=ZabbixHostInterfaceTypeChoices.SNMP, interfaceid=10002, ip=self.ip, port=161, snmp_version=ZabbixHostInterfaceSNMPVersionChoices.SNMPV2, snmp_community='public'
        )

        # IPMI interface
        self.interface_ipmi = ZabbixHostInterface.objects.create(assigned_object_type=self.device_ct, assigned_object_id=self.device.id, zabbixserver=self.zabbixserver, type=ZabbixHostInterfaceTypeChoices.IPMI, interfaceid=10003, port=161, ipmi_username='admin', ipmi_password='password')

        # Simulate Host object with plugin settings
        class DummyHost:
            def __init__(self, device, device_ct, proxy, proxy_group, server):
                self.device = device
                self.assigned_object = device
                self.assigned_object_id = device.id
                self.assigned_object_type = device_ct
                self.hostid = '12345'
                self.zabbixproxy = proxy
                self.zabbixproxygroup = proxy_group
                self.zabbixserver = server
                self.assigned_objects = {'hostgroups': []}

            def save(self):
                pass

            def update_sync_info(self, success, message):
                print(f'Sync: {success}, Msg: {message}')

        self.obj = DummyHost(device=self.device, device_ct=self.device_ct, proxy=self.zabbix_proxy, proxy_group=self.proxygroup, server=self.zabbixserver)

        class DummyAPI:
            def __init__(self):
                self.host = self.Host()
                self.hostinterface = self.HostInterface()
                self.template = self.Template()
                self.hostgroup = self.Hostgroup()
                self.maintenance = self.Maintenance()

            class Host:
                def delete(self, hostids):
                    return ['deleted']  # pragma: no cover

                def get(self, **kwargs):
                    return [{'macros': [], 'hostid': kwargs.get('hostids')}]

            class HostInterface:
                def get(self, **kwargs):
                    return []

                def delete(self, interfaceid):
                    return ['deleted']  # pragma: no cover

            class Template:
                def get(self, **kwargs):
                    return [{'templateid': 1}]

            class Hostgroup:
                pass

            class Maintenance:
                def get(self, **kwargs):
                    # Return no maintenances so delete() can proceed
                    return []

        dummy_api = DummyAPI()

        self.sync = HostSync(api=dummy_api, netbox_obj=self.obj, obj=self.obj)
        # Assign context separately so it's not lost
        self.sync.context = {
            'all_objects': {
                'hostinterfaces': [self.interface_agent, self.interface_snmp, self.interface_ipmi],
                'macros': [],
                'templates': [],
                'tags': [],
                'hostinventory': None,
            }
        }

        class PluginSettings:
            class StatusMapping:
                device = {
                    'active': ZabbixHostStatus.ENABLED,
                    'offline': ZabbixHostStatus.DISABLED,
                }

            statusmapping = StatusMapping()

            class SNMPConfig:
                snmp_community = '{$COMMUNITY}'
                snmp_authpass = '{$AUTH_PASS}'
                snmp_privpass = '{$PRIV_PASS}'

            snmpconfig = SNMPConfig()

            class SOT:
                hostmacro = SyncSOT.ZABBIX
                hosttemplate = SyncSOT.NETBOX

            sot = SOT()
            attach_objtag = True
            objtag_type = 'nb_type'
            objtag_id = 'nb_id'

        self.sync.pluginsettings = PluginSettings()

    def test_get_create_params(self):
        params = self.sync.get_create_params()
        self.assertIn('host', params)
        self.assertEqual(params['status'], 0)
        self.assertIn('macros', params)
        self.assertIn('tls_connect', params)
        self.assertIn('ipmi_username', params)

    def test_get_update_params(self):
        update_params = self.sync.get_update_params()
        self.assertIn('hostid', update_params)

    def test_get_macros_snmpv2_only(self):
        macros = self.sync.get_macros()
        self.assertTrue(any(m['macro'] == '{$COMMUNITY}' for m in macros['macros']))
        self.assertFalse(any(m['macro'] == '{$AUTH_PASS}' for m in macros['macros']))
        self.assertFalse(any(m['macro'] == '{$PRIV_PASS}' for m in macros['macros']))

    def test_get_macros_snmpv3_only(self):
        # Replace SNMPv2 interface with SNMPv3
        self.interface_snmp.delete()
        from nbxsync.choices import ZabbixInterfaceSNMPV3SecurityLevelChoices

        self.interface_snmpv3 = ZabbixHostInterface.objects.create(
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.id,
            zabbixserver=self.zabbixserver,
            type=ZabbixHostInterfaceTypeChoices.SNMP,
            ip=self.ip,
            port=161,
            snmp_version=ZabbixHostInterfaceSNMPVersionChoices.SNMPV3,
            snmpv3_security_level=ZabbixInterfaceSNMPV3SecurityLevelChoices.AUTHPRIV,
            snmpv3_authentication_passphrase='authpass',
            snmpv3_privacy_passphrase='privpass',
            interfaceid=10004,
        )

        self.sync.context['all_objects']['hostinterfaces'] = [self.interface_agent, self.interface_snmpv3, self.interface_ipmi]

        macros = self.sync.get_macros()
        self.assertTrue(any(m['macro'] == '{$AUTH_PASS}' for m in macros['macros']))
        self.assertTrue(any(m['macro'] == '{$PRIV_PASS}' for m in macros['macros']))
        self.assertFalse(any(m['macro'] == '{$COMMUNITY}' for m in macros['macros']))

    def test_get_hostinterface_attributes(self):
        attrs = self.sync.get_hostinterface_attributes()
        self.assertEqual(attrs['tls_connect'], 1)
        self.assertEqual(attrs['ipmi_username'], 'admin')

    def test_get_hostinterface_types(self):
        types = self.sync.get_hostinterface_types()
        self.assertIn(ZabbixHostInterfaceTypeChoices.AGENT, types)
        self.assertIn(ZabbixHostInterfaceTypeChoices.SNMP, types)
        self.assertIn(ZabbixHostInterfaceTypeChoices.IPMI, types)

    def test_get_proxy_or_proxygroup(self):
        result = self.sync.get_proxy_or_proxygroup()
        self.assertEqual(result['monitored_by'], 2)
        self.assertEqual(result['proxyid'], self.zabbix_proxy.proxyid)
        self.assertEqual(result['proxy_groupid'], self.proxygroup.proxy_groupid)

    def test_delete_successful(self):
        self.sync.delete()
        self.assertIsNone(self.obj.hostid)

    def test_verify_hostinterfaces(self):
        self.sync.verify_hostinterfaces()

    def test_get_name_value(self):
        name = self.sync.get_name_value()
        self.assertEqual(name, self.device.name)

    def test_result_key(self):
        self.assertEqual(self.sync.result_key(), 'hostids')

    def test_get_create_params_sets_disabled_status(self):
        # Change status to 'offline' to trigger DISABLED mapping
        self.obj.assigned_object.status = 'offline'

        params = self.sync.get_create_params()
        self.assertEqual(params['status'], 1)  # 1 = Disabled/Not Monitored

    def test_get_defined_macros_basic(self):
        class DummyZabbixMacro:
            def __init__(self, type_, description):
                self.type = type_
                self.description = description

        class DummyMacro:
            def __init__(self):
                self.zabbixmacro = DummyZabbixMacro(type_=1, description='Test Macro')
                self.value = 'secret-value'

            def __str__(self):
                return '{$TEST_MACRO}'

        macro_obj = DummyMacro()

        self.sync.context['all_objects']['macros'] = [macro_obj]

        result = self.sync.get_defined_macros()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['macro'], '{$TEST_MACRO}')
        self.assertEqual(result[0]['type'], 1)
        self.assertEqual(result[0]['description'], 'Test Macro')
        self.assertEqual(result[0]['value'], 'secret-value')

    def test_get_defined_macros_includes_zabbix_only(self):
        class DummyZabbixMacro:
            def __init__(self, type_, description):
                self.type = type_
                self.description = description

        class DummyMacro:
            def __init__(self):
                self.zabbixmacro = DummyZabbixMacro(type_=1, description='From NetBox')
                self.value = 'nb-value'

            def __str__(self):
                return '{$FROM_NETBOX}'

        # One macro from NetBox context
        netbox_macro = DummyMacro()
        self.sync.context['all_objects']['macros'] = [netbox_macro]

        # Patch API response to simulate a Zabbix-only macro
        self.sync.api.host.get = lambda **kwargs: [
            {
                'hostid': self.obj.hostid,
                'macros': [
                    {'macro': '{$FROM_ZABBIX}', 'value': 'zb-value', 'description': 'From Zabbix', 'type': 1},
                    {'macro': '{$FROM_NETBOX}', 'value': 'nb-value', 'description': 'From NetBox', 'type': 1},
                ],
            }
        ]

        # Ensure pluginsettings is set to pull macros from Zabbix
        self.sync.pluginsettings.sot.hostmacro = SyncSOT.ZABBIX

        result = self.sync.get_defined_macros()

        # Check that both macros are returned
        macros = {m['macro']: m for m in result}
        self.assertIn('{$FROM_NETBOX}', macros)
        self.assertIn('{$FROM_ZABBIX}', macros)

        self.assertEqual(macros['{$FROM_ZABBIX}']['value'], 'zb-value')
        self.assertEqual(macros['{$FROM_ZABBIX}']['description'], 'From Zabbix')
        self.assertEqual(macros['{$FROM_ZABBIX}']['type'], 1)

    def test_get_templates_clear_attributes_no_hostid(self):
        self.obj.hostid = None
        result = self.sync.get_templates_clear_attributes()
        self.assertEqual(result, {})  # Confirm early return

    def test_get_templates_clear_attributes_filters_invalid_template_entries(self):
        # Simulate current template in Zabbix
        self.sync.api.template.get = lambda **kwargs: [{'templateid': 10}]

        # This will skip the str and the dict without 'templateid'
        self.sync.templates = {'templates': [{'templateid': 9}, 'not_a_dict', {'name': 'missing_templateid_key'}]}

        self.sync.pluginsettings.sot.hosttemplate = SyncSOT.NETBOX
        result = self.sync.get_templates_clear_attributes()

        # Zabbix template 10 should be marked for clearing (since not in intended)
        self.assertEqual(result, {'templates_clear': [{'templateid': 10}]})

    def test_get_templates_clear_attributes_sot_zabbix_merges_templates(self):
        # Current templates from Zabbix
        self.sync.api.template.get = lambda **kwargs: [{'templateid': 20}, {'templateid': 30}]

        # Only one intended template
        self.sync.templates = {'templates': [{'templateid': 20}]}

        self.sync.pluginsettings.sot.hosttemplate = SyncSOT.ZABBIX
        result = self.sync.get_templates_clear_attributes()

        # Should not clear anything
        self.assertEqual(result, {})

        # The missing templateid (30) should be appended
        template_ids = {tpl['templateid'] for tpl in self.sync.templates['templates']}
        self.assertIn(30, template_ids)
        self.assertIn(20, template_ids)  # Existing one still there

    def test_get_template_attributes_with_none(self):
        class DummyZabbixTemplate:
            def __init__(self):
                self.templateid = 101
                self.interface_requirements = [HostInterfaceRequirementChoices.NONE]

        class DummyAssignedTemplate:
            def __init__(self):
                self.zabbixtemplate = DummyZabbixTemplate()

        self.sync.context['all_objects']['templates'] = [DummyAssignedTemplate()]

        result = self.sync.get_template_attributes()
        self.assertIn({'templateid': 101}, result['templates'])

    def test_get_template_attributes_with_any_but_no_interfaces(self):
        class DummyZabbixTemplate:
            def __init__(self):
                self.templateid = 102
                self.interface_requirements = [HostInterfaceRequirementChoices.ANY]

        class DummyAssignedTemplate:
            def __init__(self):
                self.zabbixtemplate = DummyZabbixTemplate()

        self.sync.context['all_objects']['templates'] = [DummyAssignedTemplate()]
        self.sync.context['all_objects']['hostinterfaces'] = []  # No interfaces

        result = self.sync.get_template_attributes()
        self.assertNotIn({'templateid': 102}, result['templates'])
        self.assertEqual(result['templates'], [])

    def test_get_template_attributes_with_specific_interface_present(self):
        class DummyZabbixTemplate:
            def __init__(self):
                self.templateid = 103
                self.interface_requirements = [HostInterfaceRequirementChoices.SNMP]

        class DummyAssignedTemplate:
            def __init__(self):
                self.zabbixtemplate = DummyZabbixTemplate()

        self.sync.context['all_objects']['templates'] = [DummyAssignedTemplate()]
        self.sync.context['all_objects']['hostinterfaces'] = [self.interface_snmp]

        result = self.sync.get_template_attributes()
        self.assertIn({'templateid': 103}, result['templates'])

    def test_get_template_attributes_with_specific_interface_missing(self):
        class DummyZabbixTemplate:
            def __init__(self):
                self.templateid = 104
                self.interface_requirements = [HostInterfaceRequirementChoices.AGENT]

        class DummyAssignedTemplate:
            def __init__(self):
                self.zabbixtemplate = DummyZabbixTemplate()

        self.sync.context['all_objects']['templates'] = [DummyAssignedTemplate()]
        self.sync.context['all_objects']['hostinterfaces'] = [self.interface_snmp]  # No AGENT interface

        result = self.sync.get_template_attributes()
        self.assertNotIn({'templateid': 104}, result['templates'])
        self.assertEqual(result['templates'], [])

    def test_get_tag_attributes(self):
        class DummyZabbixTag:
            def __init__(self, tag):
                self.tag = tag

        class DummyAssignedTag:
            def __init__(self):
                self.zabbixtag = DummyZabbixTag('env')

            def render(self):
                return ('production', True)

        dummy_tag = DummyAssignedTag()

        self.sync.context['all_objects']['tags'] = [dummy_tag]

        result = self.sync.get_tag_attributes()
        self.assertEqual(result, {'tags': [{'tag': 'env', 'value': 'production'}, {'tag': 'nb_type', 'value': str(type(self.device).__name__).lower()}, {'tag': 'nb_id', 'value': str(self.device.id)}]})

    def test_get_groups(self):
        class DummyZabbixHostGroup:
            def __init__(self, groupid, value=''):
                self.groupid = groupid
                self.value = value

        class DummyGroup:
            def __init__(self, groupid, value=''):
                self.zabbixhostgroup = DummyZabbixHostGroup(groupid)

        # Inject dummy hostgroups into obj.assigned_objects
        self.obj.assigned_objects['hostgroups'] = [DummyGroup(groupid=1001), DummyGroup(groupid=1002)]

        result = self.sync.get_groups()
        self.assertEqual(result, [{'groupid': 1001}, {'groupid': 1002}])

    def test_delete_skips_when_hostid_missing(self):
        self.obj.hostid = None  # Simulate already-deleted host

        # Spy on update_sync_info
        messages = []

        def fake_update_sync_info(success, message):
            messages.append((success, message))

        self.obj.update_sync_info = fake_update_sync_info

        self.sync.delete()

        # Assert it was called with the expected failure message
        self.assertEqual(len(messages), 1)
        self.assertFalse(messages[0][0])  # success=False
        self.assertIn('Host already deleted or missing host ID', messages[0][1])

    def test_get_hostinventory_none(self):
        self.sync.context['all_objects']['hostinventory'] = None
        result = self.sync.get_hostinventory()
        self.assertEqual(result, {'inventory_mode': 0})

    def test_get_hostinventory_with_rendered_fields(self):
        class DummyHostInventory:
            def __init__(self):
                self.inventory_mode = 1

            def render_all_fields(self):
                return {
                    'serialnumber': ('ABC123', True),
                    'location': ('', True),  # Empty, should be skipped
                    'notes': ('Note here', False),  # Not successful, skipped
                    'asset_tag': ('TAG-001', True),
                }

        self.sync.context['all_objects']['hostinventory'] = DummyHostInventory()

        result = self.sync.get_hostinventory()

        self.assertEqual(result['inventory_mode'], 1)
        self.assertIn('inventory', result)
        self.assertEqual(result['inventory'], {'serialnumber': 'ABC123', 'asset_tag': 'TAG-001'})

        self.assertNotIn('notes', result['inventory'])
        self.assertNotIn('location', result['inventory'])

    def test_verify_hostinterfaces_skips_when_hostid_missing(self):
        self.obj.hostid = None  # Simulate no host ID

        # Add a spy/mock to the API to ensure it's NOT called
        called = {'hostinterface_get': False}

        def fake_get(*args, **kwargs):
            called['hostinterface_get'] = True  # pragma: no cover
            return []  # pragma: no cover

        self.sync.api.hostinterface.get = fake_get

        result = self.sync.verify_hostinterfaces()

        # Should return {} and not call the API
        self.assertEqual(result, {})
        self.assertFalse(called['hostinterface_get'])

    def test_verify_hostinterfaces_deletes_unexpected_interfaces(self):
        self.obj.hostid = '12345'

        # Expected interface (from NetBox)
        self.interface_agent.interfaceid = 1001
        self.sync.context['all_objects']['hostinterfaces'] = [self.interface_agent]

        # Zabbix returns two interfaces, one extra
        self.sync.api.hostinterface.get = lambda **kwargs: [
            {'interfaceid': 1001},  # expected, should not be deleted
            {'interfaceid': 2002},  # unexpected, should be deleted
        ]

        deleted_ids = []

        def mock_delete(interfaceid):
            deleted_ids.append(interfaceid)

        self.sync.api.hostinterface.delete = mock_delete

        self.sync.verify_hostinterfaces()

        # Only the unexpected one should be deleted
        self.assertEqual(deleted_ids, [2002])

    def test_delete_raises_runtimeerror_on_api_failure(self):
        self.obj.hostid = '12345'

        # Force api_object().delete to raise an exception
        class FailingAPIObject:
            def delete(self, hostids):
                raise Exception('Simulated API failure')

        self.sync.api_object = lambda: FailingAPIObject()

        # Spy on update_sync_info
        messages = []

        def fake_update_sync_info(success, message):
            messages.append((success, message))

        self.obj.update_sync_info = fake_update_sync_info

        with self.assertRaises(RuntimeError) as context:
            self.sync.delete()

        self.assertIn('Failed to delete host', str(context.exception))
        self.assertEqual(len(messages), 1)
        self.assertFalse(messages[0][0])  # success = False
        self.assertIn('Simulated API failure', messages[0][1])
