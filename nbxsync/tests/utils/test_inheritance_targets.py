"""Tests for hierarchy assignment targets and ConfigGroup interface expansion.

Covers the parts of the inheritance resolver that the assignment surfaces
advertise but the models used to reject or collapse: Region as an assignment
target, hierarchy-level host inventory, and ConfigGroup interfaces that share a
Zabbix type but describe different endpoints.
"""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from ipam.models import IPAddress

from dcim.models import Region, Site, SiteGroup
from utilities.testing import create_test_device

from nbxsync.choices import ZabbixHostInterfaceTypeChoices, ZabbixInterfaceTypeChoices, ZabbixInterfaceUseChoices
from nbxsync.models import (
    ZabbixConfigurationGroup,
    ZabbixConfigurationGroupAssignment,
    ZabbixHostInterface,
    ZabbixHostInventory,
    ZabbixServer,
    ZabbixTemplate,
    ZabbixTemplateAssignment,
)
from nbxsync.utils.inheritance import get_assigned_zabbixobjects


class RegionAssignmentTargetTestCase(TestCase):
    """Region is offered by the forms, documented as inherited, and must be storable."""

    def setUp(self):
        self.server = ZabbixServer.objects.create(name='Region Server', url='http://zabbix.local', token='abc123', validate_certs=True)
        self.template = ZabbixTemplate.objects.create(name='Linux by Zabbix agent', zabbixserver=self.server, templateid=10001)
        self.region = Region.objects.create(name='EMEA', slug='emea')
        self.child_region = Region.objects.create(name='Netherlands', slug='nl', parent=self.region)
        self.site = Site.objects.create(name='Amsterdam', slug='ams', region=self.child_region)
        self.device = create_test_device(name='region-device', site=self.site)

    def test_region_is_an_allowed_assignment_content_type(self):
        region_ct = ContentType.objects.get_for_model(Region)
        allowed = ContentType.objects.filter(ZabbixTemplateAssignment._meta.get_field('assigned_object_type').get_limit_choices_to())

        self.assertIn(region_ct, allowed)

    def test_template_assigned_to_parent_region_is_inherited(self):
        assignment = ZabbixTemplateAssignment.objects.create(
            zabbixtemplate=self.template,
            assigned_object_type=ContentType.objects.get_for_model(Region),
            assigned_object_id=self.region.pk,
        )
        assignment.full_clean()

        result = get_assigned_zabbixobjects(self.device)

        self.assertEqual([obj.zabbixtemplate_id for obj in result['templates']], [self.template.pk])

    def test_hostinventory_can_be_assigned_to_a_hierarchy_object(self):
        inventory = ZabbixHostInventory(
            assigned_object_type=ContentType.objects.get_for_model(SiteGroup),
            assigned_object_id=SiteGroup.objects.create(name='Datacenters', slug='dcs').pk,
            location='Rack row A',
        )

        inventory.full_clean()
        inventory.save()

        self.assertTrue(ZabbixHostInventory.objects.filter(pk=inventory.pk).exists())


class ConfigGroupInterfaceExpansionTestCase(TestCase):
    """ConfigGroup interfaces are cloned per device and must not collapse by type."""

    def setUp(self):
        self.server = ZabbixServer.objects.create(name='CG Server', url='http://zabbix.local', token='abc123', validate_certs=True)
        self.device = create_test_device(name='cg-device')
        self.configgroup = ZabbixConfigurationGroup.objects.create(name='Standard SNMP')
        ZabbixConfigurationGroupAssignment.objects.create(
            zabbixconfigurationgroup=self.configgroup,
            assigned_object_type=ContentType.objects.get_for_model(type(self.device)),
            assigned_object_id=self.device.pk,
        )

    def _cg_interface(self, port, interface_type=ZabbixInterfaceTypeChoices.DEFAULT):
        return ZabbixHostInterface.objects.create(
            zabbixserver=self.server,
            type=ZabbixHostInterfaceTypeChoices.SNMP,
            useip=ZabbixInterfaceUseChoices.IP,
            interface_type=interface_type,
            port=port,
            assigned_object_type=ContentType.objects.get_for_model(ZabbixConfigurationGroup),
            assigned_object_id=self.configgroup.pk,
        )

    def test_two_snmp_interfaces_on_different_ports_are_both_expanded(self):
        self._cg_interface(port=161)
        self._cg_interface(port=1161, interface_type=ZabbixInterfaceTypeChoices.NOTDEFAULT)

        result = get_assigned_zabbixobjects(self.device)

        ports = sorted(interface.port for interface in result['hostinterfaces'])
        self.assertEqual(ports, [161, 1161])

    def test_configgroup_interface_yields_to_an_identical_direct_interface(self):
        self._cg_interface(port=161)
        ip = IPAddress.objects.create(address='192.0.2.10/24')
        direct = ZabbixHostInterface.objects.create(
            zabbixserver=self.server,
            type=ZabbixHostInterfaceTypeChoices.SNMP,
            useip=ZabbixInterfaceUseChoices.IP,
            interface_type=ZabbixInterfaceTypeChoices.DEFAULT,
            port=161,
            ip=ip,
            assigned_object_type=ContentType.objects.get_for_model(type(self.device)),
            assigned_object_id=self.device.pk,
        )

        result = get_assigned_zabbixobjects(self.device)

        self.assertEqual([interface.pk for interface in result['hostinterfaces']], [direct.pk])

    def test_configgroup_interfaces_are_filtered_by_zabbixserver(self):
        other = ZabbixServer.objects.create(name='Other CG Server', url='http://other.local', token='xyz', validate_certs=True)
        self._cg_interface(port=161)
        ZabbixHostInterface.objects.create(
            zabbixserver=other,
            type=ZabbixHostInterfaceTypeChoices.SNMP,
            useip=ZabbixInterfaceUseChoices.IP,
            interface_type=ZabbixInterfaceTypeChoices.NOTDEFAULT,
            port=1161,
            assigned_object_type=ContentType.objects.get_for_model(ZabbixConfigurationGroup),
            assigned_object_id=self.configgroup.pk,
        )

        result = get_assigned_zabbixobjects(self.device, zabbixserver=self.server)

        ports = [interface.port for interface in result['hostinterfaces']]
        self.assertEqual(ports, [161])


class VirtualMachineDeviceLeakTestCase(TestCase):
    """A VM linked to its hosting device (NetBox 4.3+) must not inherit the
    host's hardware-tier assignments (manufacturer, device_type, role via
    'device'-prefixed chain paths). A guest is not the hypervisor's hardware.
    """

    def setUp(self):
        from virtualization.models import VirtualMachine

        from dcim.models import Manufacturer

        self.server = ZabbixServer.objects.create(name='Leak Server', url='http://zabbix.local', token='abc123', validate_certs=True)
        self.template = ZabbixTemplate.objects.create(name='Dell iDRAC by SNMP', zabbixserver=self.server, templateid=10255)
        self.dell = Manufacturer.objects.create(name='Dell', slug='dell')
        self.host = create_test_device(name='esx-host-01')
        host_type = self.host.device_type
        host_type.manufacturer = self.dell
        host_type.save()
        self.vm = VirtualMachine.objects.create(name='guest-vm-01', device=self.host)

        manufacturer_ct = ContentType.objects.get_for_model(Manufacturer)
        self.assignment = ZabbixTemplateAssignment.objects.create(
            zabbixtemplate=self.template,
            assigned_object_type=manufacturer_ct,
            assigned_object_id=self.dell.pk,
        )

    def test_device_inherits_manufacturer_template(self):
        result = get_assigned_zabbixobjects(self.host)
        self.assertIn(self.template.pk, [obj.zabbixtemplate_id for obj in result['templates']])

    def test_vm_does_not_inherit_manufacturer_template_via_associated_device(self):
        result = get_assigned_zabbixobjects(self.vm)
        self.assertNotIn(self.template.pk, [obj.zabbixtemplate_id for obj in result['templates']])
