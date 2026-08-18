"""Tests for how sync handles an OOB interface that cannot be resolved.

A device whose oob_ip is missing (never set, or cleared) cannot get its OOB
interface synced. The interface is skipped so SNMP templates are not linked to a
host without an SNMP interface, and whatever Zabbix already has is retained
unless the operator opted into inheritance-driven deletion.
"""

from unittest.mock import MagicMock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device
from ipam.models import IPAddress
from utilities.testing import create_test_device

from nbxsync.choices import ZabbixHostInterfaceTypeChoices, ZabbixInterfaceTypeChoices, ZabbixInterfaceUseChoices
from nbxsync.jobs.synchost import SyncHostJob
from nbxsync.models import ZabbixHostInterface, ZabbixServer, ZabbixServerAssignment
from nbxsync.tests.utils.test_host_binding import PluginSettingMixin
from nbxsync.utils.sync import HostSync


class OOBInterfaceSyncTestCase(PluginSettingMixin, TestCase):
    def setUp(self):
        self.device = create_test_device(name='oob-device')
        self.device_ct = ContentType.objects.get_for_model(Device)
        self.server = ZabbixServer.objects.create(name='OOB Server', url='http://zabbix.local', token='abc123', validate_certs=True)
        self.assignment = ZabbixServerAssignment.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            hostid=4242,
        )
        self.interface = ZabbixHostInterface.objects.create(
            zabbixserver=self.server,
            type=ZabbixHostInterfaceTypeChoices.SNMP,
            useip=ZabbixInterfaceUseChoices.IP,
            interface_type=ZabbixInterfaceTypeChoices.DEFAULT,
            port=161,
            use_oob_ip=True,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
        )

    def test_interface_is_skipped_and_retained_without_an_oob_ip(self):
        job = SyncHostJob(instance=self.device)

        with self.assertLogs('nbxsync.jobs.synchost', level='WARNING') as logs:
            all_objects = job._resolve_all_objects(self.assignment)

        self.assertEqual(all_objects['hostinterfaces'], [])
        self.assertEqual([hi.pk for hi in all_objects['retained_hostinterfaces']], [self.interface.pk])
        self.assertIn('allow_inherited_deletion', ' '.join(logs.output))

    def test_interface_is_not_retained_when_inherited_deletion_is_allowed(self):
        self._set_plugin_setting('allow_inherited_deletion', True)
        job = SyncHostJob(instance=self.device)

        with self.assertLogs('nbxsync.jobs.synchost', level='WARNING'):
            all_objects = job._resolve_all_objects(self.assignment)

        self.assertEqual(all_objects['hostinterfaces'], [])
        self.assertNotIn('retained_hostinterfaces', all_objects)

    def test_interface_is_synced_when_the_device_has_an_oob_ip(self):
        self.device.oob_ip = IPAddress.objects.create(address='192.0.2.50/24')
        self.device.save()
        job = SyncHostJob(instance=self.device)

        all_objects = job._resolve_all_objects(self.assignment)

        self.assertEqual([hi.pk for hi in all_objects['hostinterfaces']], [self.interface.pk])
        self.assertNotIn('retained_hostinterfaces', all_objects)

    def test_retained_interface_is_not_deleted_from_zabbix(self):
        api = MagicMock()
        api.hostinterface.get.return_value = [
            {
                'interfaceid': '900',
                'type': str(int(ZabbixHostInterfaceTypeChoices.SNMP)),
                'main': str(int(ZabbixInterfaceTypeChoices.DEFAULT)),
                'useip': '1',
                'port': '161',
                'dns': '',
            },
        ]
        all_objects = {
            '_instance': self.device,
            'hostinterfaces': [],
            'retained_hostinterfaces': [self.interface],
        }

        HostSync(api=api, netbox_obj=self.assignment, all_objects=all_objects).verify_hostinterfaces()

        api.hostinterface.delete.assert_not_called()

    def test_retained_interface_types_keep_snmp_templates_linked(self):
        """Retained OOB SNMP must still count for template interface requirements."""
        from nbxsync.choices import HostInterfaceRequirementChoices
        from nbxsync.models import ZabbixTemplate, ZabbixTemplateAssignment

        template = ZabbixTemplate.objects.create(
            name='SNMP Template',
            zabbixserver=self.server,
            templateid=5555,
            interface_requirements=[HostInterfaceRequirementChoices.SNMP],
        )
        assignment = ZabbixTemplateAssignment(
            zabbixtemplate=template,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
        )
        api = MagicMock()
        api.template.get.return_value = [{'templateid': '5555'}]
        all_objects = {
            '_instance': self.device,
            'hostinterfaces': [],
            'retained_hostinterfaces': [self.interface],
            'templates': [assignment],
        }
        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=all_objects)

        self.assertEqual(sync.get_hostinterface_types(), [ZabbixHostInterfaceTypeChoices.SNMP])
        templates = sync.get_template_attributes()
        self.assertEqual(templates, {'templates': [{'templateid': 5555}]})
        # get_templates_clear_attributes reads self.templates (set during HostSync update).
        sync.templates = templates
        self.assertEqual(sync.get_templates_clear_attributes(), {'templates_clear': []})

    def test_retained_interface_with_persisted_interfaceid_is_not_deleted(self):
        """Previously synced OOB rows keep interfaceid; retain must honour it."""
        self.interface.interfaceid = 900
        self.interface.save(update_fields=['interfaceid'])

        api = MagicMock()
        api.hostinterface.get.return_value = [
            {
                'interfaceid': '900',
                'type': str(int(ZabbixHostInterfaceTypeChoices.SNMP)),
                'main': str(int(ZabbixInterfaceTypeChoices.DEFAULT)),
                'useip': '1',
                'port': '161',
                'dns': '',
            },
        ]
        all_objects = {
            '_instance': self.device,
            'hostinterfaces': [],
            'retained_hostinterfaces': [self.interface],
        }

        HostSync(api=api, netbox_obj=self.assignment, all_objects=all_objects).verify_hostinterfaces()

        api.hostinterface.delete.assert_not_called()

    def test_unknown_interface_is_still_deleted_from_zabbix(self):
        api = MagicMock()
        api.hostinterface.get.return_value = [
            {'interfaceid': '901', 'type': str(int(ZabbixHostInterfaceTypeChoices.JMX)), 'useip': '1', 'port': '12345'},
        ]
        all_objects = {'_instance': self.device, 'hostinterfaces': []}

        HostSync(api=api, netbox_obj=self.assignment, all_objects=all_objects).verify_hostinterfaces()

        api.hostinterface.delete.assert_called_once_with(901)

    @patch('nbxsync.jobs.synchost.safe_sync')
    @patch.object(SyncHostJob, 'verify_hostinterfaces')
    def test_sync_skips_interface_sync_for_unresolvable_oob_interface(self, mock_verify, mock_safe_sync):
        job = SyncHostJob(instance=self.device)

        with self.assertLogs('nbxsync.jobs.synchost', level='WARNING'):
            job.sync_host(self.assignment)

        synced_classes = [getattr(call.args[0], '__name__', None) for call in mock_safe_sync.call_args_list]
        self.assertNotIn('HostInterfaceSync', synced_classes)
