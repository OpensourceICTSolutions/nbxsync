from unittest.mock import Mock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import DeviceType, Manufacturer
from utilities.testing import create_test_device

from nbxsync.models import (
    ZabbixHostgroup,
    ZabbixHostgroupAssignment,
    ZabbixMacro,
    ZabbixMacroAssignment,
    ZabbixServer,
    ZabbixTag,
    ZabbixTagAssignment,
    ZabbixTemplate,
    ZabbixTemplateAssignment,
)
from nbxsync.utils.inheritance import resolve_inherited_zabbix_assignments


class ResolveInheritedAssignmentsTestCase(TestCase):
    def setUp(self):
        self.device = create_test_device(name='TestDev')
        self.manufacturer = Manufacturer.objects.get(id=self.device.device_type.manufacturer.id)
        self.device_type = DeviceType.objects.get(id=self.device.device_type.id)
        self.zabbixserver = ZabbixServer.objects.create(name='Zabbix1', url='http://zabbix.local', token='abc123', validate_certs=True)

        # Create related inherited objects
        self.template = ZabbixTemplate.objects.create(name='Template1', zabbixserver=self.zabbixserver, templateid=101)
        self.macro = ZabbixMacro.objects.create(macro='{$ENV}', value='prod', type=0, hostmacroid=201)
        self.tag = ZabbixTag.objects.create(tag='region', value='us-east')
        self.hostgroup = ZabbixHostgroup.objects.create(name='Core', value='core-group', groupid=401, zabbixserver=self.zabbixserver)

        ct = ContentType.objects.get_for_model(self.device_type)

        ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=ct, assigned_object_id=self.device_type.pk)
        ZabbixMacroAssignment.objects.create(zabbixmacro=self.macro, assigned_object_type=ct, assigned_object_id=self.device_type.pk, value='inherited')
        ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=ct, assigned_object_id=self.device_type.pk)
        ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=ct, assigned_object_id=self.device_type.pk)

    @patch('nbxsync.utils.inheritance.get_plugin_settings')
    def test_resolve_inherited_assignments(self, mock_settings):
        # Patch plugin settings to define inheritance path
        mock_settings.return_value.inheritance_chain = [('device_type',)]

        result = resolve_inherited_zabbix_assignments(self.device)

        self.assertEqual(len(result['templates']), 1)
        self.assertEqual(len(result['macros']), 1)
        self.assertEqual(len(result['tags']), 1)
        self.assertEqual(len(result['hostgroups']), 1)

        template = list(result['templates'].values())[0]
        macro = list(result['macros'].values())[0]
        tag = list(result['tags'].values())[0]
        group = list(result['hostgroups'].values())[0]

        # Ensure inherited_from is set
        self.assertEqual(template._inherited_from, 'Device Type')
        self.assertEqual(macro._inherited_from, 'Device Type')
        self.assertEqual(tag._inherited_from, 'Device Type')
        self.assertEqual(group._inherited_from, 'Device Type')

    @patch('nbxsync.utils.inheritance.get_plugin_settings')
    def test_resolve_path_returns_none(self, mock_settings):
        # Define a bogus inheritance path that will not resolve
        mock_settings.return_value.inheritance_chain = [('nonexistent',)]

        # Create a dummy object with no such attribute
        dummy = Mock(spec=[])
        dummy.__class__.__name__ = 'DummyObject'

        result = resolve_inherited_zabbix_assignments(dummy)

        # Assert that no inherited objects were found
        self.assertEqual(result['templates'], {})
        self.assertEqual(result['macros'], {})
        self.assertEqual(result['tags'], {})
        self.assertEqual(result['hostgroups'], {})
