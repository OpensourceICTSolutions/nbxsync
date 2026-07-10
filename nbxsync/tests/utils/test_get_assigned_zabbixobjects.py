from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device, DeviceType, Manufacturer, Site, SiteGroup
from utilities.testing import create_test_device

from nbxsync.choices import ZabbixProxyTypeChoices
from nbxsync.models import ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixHostInventory, ZabbixMacro, ZabbixMacroAssignment, ZabbixProxy, ZabbixServer, ZabbixServerAssignment, ZabbixTag, ZabbixTagAssignment, ZabbixTemplate, ZabbixTemplateAssignment
from nbxsync.utils.inheritance import get_assigned_zabbixobjects


class GetAssignedZabbixObjectsTestCase(TestCase):
    def setUp(self):
        self.device = create_test_device(name='TestDev')
        self.manufacturer = Manufacturer.objects.get(id=self.device.device_type.manufacturer.id)
        self.device_type = DeviceType.objects.get(id=self.device.device_type.id)

        self.device_ct = ContentType.objects.get_for_model(Device)
        self.manufacturer_ct = ContentType.objects.get_for_model(Manufacturer)
        self.site_ct = ContentType.objects.get_for_model(Site)
        self.sitegroup_ct = ContentType.objects.get_for_model(SiteGroup)

        self.server = ZabbixServer.objects.create(name='Zabbix1', url='http://localhost', token='abc123', validate_certs=True)

        self.template = ZabbixTemplate.objects.create(name='Template A', zabbixserver=self.server, templateid=1001)
        self.macro = ZabbixMacro.objects.create(macro='{$USER}', value='admin', type=1, hostmacroid=901)
        self.tag = ZabbixTag.objects.create(tag='env', value='prod')
        self.group = ZabbixHostgroup.objects.create(name='ProdGroup', groupid=201, value='prod', zabbixserver=self.server)

        self.site = self.device.site
        self.sitegroup = SiteGroup.objects.create(name='Site Group 1', slug='site-group-1')
        self.site.group = self.sitegroup
        self.site.save()

        self.proxy = ZabbixProxy.objects.create(
            name='Proxy1',
            zabbixserver=self.server,
            operating_mode=ZabbixProxyTypeChoices.ACTIVE,
            local_address='10.0.0.1',
            local_port=10051,
        )

    def test_inherited_assignments(self):
        self.template_assignment = ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=self.manufacturer_ct, assigned_object_id=self.manufacturer.pk)
        self.macro_assignment = ZabbixMacroAssignment.objects.create(zabbixmacro=self.macro, assigned_object_type=self.manufacturer_ct, assigned_object_id=self.manufacturer.pk, value='mval')
        self.tag_assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.manufacturer_ct, assigned_object_id=self.manufacturer.pk)
        self.group_assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.group, assigned_object_type=self.manufacturer_ct, assigned_object_id=self.manufacturer.pk)

        result = get_assigned_zabbixobjects(self.device)

        self.assertEqual(len(result['templates']), 1)
        self.assertEqual(len(result['macros']), 1)
        self.assertEqual(len(result['tags']), 1)
        self.assertEqual(len(result['hostgroups']), 1)

    def test_direct_assignments(self):
        self.template_assignment = ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=self.device_ct, assigned_object_id=self.device.pk)
        self.macro_assignment = ZabbixMacroAssignment.objects.create(zabbixmacro=self.macro, assigned_object_type=self.device_ct, assigned_object_id=self.device.pk, value='mval')
        self.tag_assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.device.pk)
        self.group_assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.group, assigned_object_type=self.device_ct, assigned_object_id=self.device.pk)

        result = get_assigned_zabbixobjects(self.device)

        self.assertEqual(len(result['templates']), 1)
        self.assertEqual(len(result['macros']), 1)
        self.assertEqual(len(result['tags']), 1)
        self.assertEqual(len(result['hostgroups']), 1)

    def test_inherited_server_assignment_from_site(self):
        ZabbixServerAssignment.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.site_ct,
            assigned_object_id=self.site.pk,
            zabbixproxy=self.proxy,
        )

        result = get_assigned_zabbixobjects(self.device)

        self.assertEqual(len(result['server_assignments']), 1)
        sa = result['server_assignments'][0]
        self.assertEqual(sa.zabbixserver, self.server)
        self.assertEqual(sa.zabbixproxy, self.proxy)

    def test_inherited_server_assignment_from_sitegroup(self):
        ZabbixServerAssignment.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.sitegroup_ct,
            assigned_object_id=self.sitegroup.pk,
            zabbixproxy=self.proxy,
        )

        result = get_assigned_zabbixobjects(self.device)

        self.assertEqual(len(result['server_assignments']), 1)
        sa = result['server_assignments'][0]
        self.assertEqual(sa.zabbixserver, self.server)
        self.assertEqual(sa.zabbixproxy, self.proxy)

    def test_direct_server_assignment_takes_priority_over_inherited(self):
        proxy_direct = ZabbixProxy.objects.create(
            name='Proxy2',
            zabbixserver=self.server,
            operating_mode=ZabbixProxyTypeChoices.ACTIVE,
            local_address='10.0.0.2',
            local_port=10051,
        )

        # Direct assignment on the device
        ZabbixServerAssignment.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            zabbixproxy=proxy_direct,
        )
        # Inherited assignment on the site
        ZabbixServerAssignment.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.site_ct,
            assigned_object_id=self.site.pk,
            zabbixproxy=self.proxy,
        )

        result = get_assigned_zabbixobjects(self.device)

        # Both should be present (direct + inherited)
        self.assertEqual(len(result['server_assignments']), 1)
        sa = result['server_assignments'][0]
        # Direct takes priority
        self.assertEqual(sa.zabbixproxy, proxy_direct)

    def test_inherited_hostinventory_from_manufacturer(self):
        ZabbixHostInventory.objects.create(
            assigned_object_type=self.manufacturer_ct,
            assigned_object_id=self.manufacturer.pk,
            inventory_mode=1,
        )

        result = get_assigned_zabbixobjects(self.device)

        self.assertIsNotNone(result['hostinventory'])
        self.assertEqual(result['hostinventory'].inventory_mode, 1)

    def test_no_assignments_returns_empty(self):
        result = get_assigned_zabbixobjects(self.device)

        self.assertEqual(result['templates'], [])
        self.assertEqual(result['macros'], [])
        self.assertEqual(result['tags'], [])
        self.assertEqual(result['hostgroups'], [])
        self.assertEqual(result['server_assignments'], [])
        self.assertIsNone(result['hostinventory'])
        self.assertIsNone(result['configurationgroup'])
