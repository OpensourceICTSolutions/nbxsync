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


class TagAssignmentTargetTestCase(TestCase):
    """NetBox Tags are assignment targets: an object carrying the tag inherits
    the assignment at object level; removing the tag removes the membership."""

    def setUp(self):
        from virtualization.models import VirtualMachine

        from extras.models import Tag as NetBoxTag

        self.server = ZabbixServer.objects.create(name='TagTarget Zabbix', url='http://zabbix.local', token='abc123', validate_certs=True)
        self.other_server = ZabbixServer.objects.create(name='Other Zabbix', url='http://zabbix2.local', token='def456', validate_certs=True)
        self.hostgroup = ZabbixHostgroup.objects.create(name='Priority/Critical', value='Priority/Critical', zabbixserver=self.server)
        self.netbox_tag = NetBoxTag.objects.create(name='critical', slug='critical')
        self.tag_ct = ContentType.objects.get_for_model(NetBoxTag)
        self.assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.tag_ct, assigned_object_id=self.netbox_tag.pk)
        self.device = create_test_device(name='TaggedDev')
        self.vm = VirtualMachine.objects.create(name='TaggedVM')
        self.untagged = create_test_device(name='PlainDev')

    def test_tagged_device_inherits_with_tag_label(self):
        self.device.tags.add(self.netbox_tag)
        result = get_assigned_zabbixobjects(self.device)
        groups = result['hostgroups']
        self.assertIn(self.hostgroup.pk, [g.zabbixhostgroup_id for g in groups])
        match = next(g for g in groups if g.zabbixhostgroup_id == self.hostgroup.pk)
        self.assertEqual(getattr(match, '_inherited_from', None), 'Tag: critical')

    def test_untagged_device_gets_nothing(self):
        result = get_assigned_zabbixobjects(self.untagged)
        self.assertNotIn(self.hostgroup.pk, [g.zabbixhostgroup_id for g in result['hostgroups']])

    def test_tag_removed_membership_leaves(self):
        self.device.tags.add(self.netbox_tag)
        self.assertIn(self.hostgroup.pk, [g.zabbixhostgroup_id for g in get_assigned_zabbixobjects(self.device)['hostgroups']])
        self.device.tags.remove(self.netbox_tag)
        self.assertNotIn(self.hostgroup.pk, [g.zabbixhostgroup_id for g in get_assigned_zabbixobjects(self.device)['hostgroups']])

    def test_tagged_vm_inherits(self):
        self.vm.tags.add(self.netbox_tag)
        result = get_assigned_zabbixobjects(self.vm)
        self.assertIn(self.hostgroup.pk, [g.zabbixhostgroup_id for g in result['hostgroups']])

    def test_server_scoping_filters_tag_targeted_hostgroups(self):
        self.device.tags.add(self.netbox_tag)
        result = get_assigned_zabbixobjects(self.device, zabbixserver=self.other_server)
        self.assertNotIn(self.hostgroup.pk, [g.zabbixhostgroup_id for g in result['hostgroups']])

    def test_tag_targeted_hostinterface_resolves_with_device_ip(self):
        from ipam.models import IPAddress

        from nbxsync.choices import ZabbixHostInterfaceTypeChoices, ZabbixInterfaceTypeChoices, ZabbixInterfaceUseChoices
        from nbxsync.models import ZabbixHostInterface

        tag_if = ZabbixHostInterface(
            zabbixserver=self.server,
            type=ZabbixHostInterfaceTypeChoices.SNMP,
            interface_type=ZabbixInterfaceTypeChoices.DEFAULT,
            useip=ZabbixInterfaceUseChoices.IP,
            port=161,
            dns='',
            assigned_object_type=self.tag_ct,
            assigned_object_id=self.netbox_tag.pk,
        )
        tag_if.full_clean()
        tag_if.save()
        self.assertIsNone(tag_if.ip)  # endpoint cleared — resolved per device

        self.device.tags.add(self.netbox_tag)
        result = get_assigned_zabbixobjects(self.device)
        matches = [hi for hi in result['hostinterfaces'] if int(hi.type) == ZabbixHostInterfaceTypeChoices.SNMP and int(hi.port) == 161]
        self.assertEqual(len(matches), 1)
        self.assertTrue(getattr(matches[0], '_is_inherited_copy', False))
        self.assertEqual(getattr(matches[0], '_inherited_from', None), 'Tag: critical')

        self.untagged_ifaces = [hi for hi in get_assigned_zabbixobjects(self.untagged)['hostinterfaces'] if int(hi.port) == 161]
        self.assertEqual(self.untagged_ifaces, [])


class VirtualMachineDeviceLeakTestCase(TestCase):
    """A VM linked to its hosting device (NetBox 4.3+) must not inherit the
    host's hardware-tier assignments (manufacturer etc. via 'device'-prefixed
    chain paths). A guest is not the hypervisor's hardware.
    """

    def setUp(self):
        from virtualization.models import VirtualMachine

        self.server = ZabbixServer.objects.create(name='Leak Server', url='http://zabbix.local', token='abc123', validate_certs=True)
        self.template = ZabbixTemplate.objects.create(name='Vendor OOB by SNMP', zabbixserver=self.server, templateid=10255)
        self.dell = Manufacturer.objects.create(name='Dell', slug='dell-oss')
        self.host = create_test_device(name='esx-host-01')
        host_type = self.host.device_type
        host_type.manufacturer = self.dell
        host_type.save()
        self.vm = VirtualMachine.objects.create(name='guest-vm-01', device=self.host)

        self.assignment = ZabbixTemplateAssignment.objects.create(
            zabbixtemplate=self.template,
            assigned_object_type=ContentType.objects.get_for_model(Manufacturer),
            assigned_object_id=self.dell.pk,
        )

    def test_device_inherits_manufacturer_template(self):
        result = get_assigned_zabbixobjects(self.host)
        self.assertIn(self.template.pk, [obj.zabbixtemplate_id for obj in result['templates']])

    def test_vm_does_not_inherit_manufacturer_template_via_associated_device(self):
        result = get_assigned_zabbixobjects(self.vm)
        self.assertNotIn(self.template.pk, [obj.zabbixtemplate_id for obj in result['templates']])
