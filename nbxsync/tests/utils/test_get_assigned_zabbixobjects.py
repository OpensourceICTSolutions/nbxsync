from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device, DeviceType, Manufacturer
from utilities.testing import create_test_device

from nbxsync.models import ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixMacro, ZabbixMacroAssignment, ZabbixServer, ZabbixTag, ZabbixTagAssignment, ZabbixTemplate, ZabbixTemplateAssignment
from nbxsync.utils.inheritance import get_assigned_zabbixobjects


class GetAssignedZabbixObjectsTestCase(TestCase):
    def setUp(self):
        self.device = create_test_device(name='TestDev')
        self.manufacturer = Manufacturer.objects.get(id=self.device.device_type.manufacturer.id)
        self.device_type = DeviceType.objects.get(id=self.device.device_type.id)

        self.device_ct = ContentType.objects.get_for_model(Device)
        self.manufacturer_ct = ContentType.objects.get_for_model(Manufacturer)

        self.server = ZabbixServer.objects.create(name='Zabbix1', url='http://localhost', token='abc123', validate_certs=True)

        self.template = ZabbixTemplate.objects.create(name='Template A', zabbixserver=self.server, templateid=1001)
        self.macro = ZabbixMacro.objects.create(macro='{$USER}', value='admin', type=1, hostmacroid=901)
        self.tag = ZabbixTag.objects.create(tag='env', value='prod')
        self.group = ZabbixHostgroup.objects.create(name='ProdGroup', groupid=201, value='prod', zabbixserver=self.server)

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
