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
