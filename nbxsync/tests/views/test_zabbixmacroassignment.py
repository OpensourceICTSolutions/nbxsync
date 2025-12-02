from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from virtualization.models import VirtualMachine

from dcim.models import Device
from utilities.testing import ViewTestCases, create_test_device, create_test_virtualmachine

from nbxsync.forms import ZabbixMacroAssignmentForm
from nbxsync.models import ZabbixMacro, ZabbixMacroAssignment, ZabbixServer, ZabbixTemplate


class ZabbixMacroAssignmentTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ZabbixMacroAssignment

    @classmethod
    def setUpTestData(cls):
        cls.zabbix_servers = [
            ZabbixServer(name='Zabbix Server Bulk 1', description='Test Bulk Server 1', url='http://examplebulk1.com', token='bulk1-token', validate_certs=True),
            ZabbixServer(name='Zabbix Server Bulk 2', description='Test Bulk Server 2', url='http://examplebulk2.com', token='bulk2-token', validate_certs=True),
        ]
        ZabbixServer.objects.bulk_create(cls.zabbix_servers)

        cls.zabbix_templates = [
            ZabbixTemplate(name='Template 1', templateid=1, zabbixserver=cls.zabbix_servers[0], interface_requirements=[0]),
            ZabbixTemplate(name='Template 2', templateid=2, zabbixserver=cls.zabbix_servers[0], interface_requirements=[0]),
        ]
        ZabbixTemplate.objects.bulk_create(cls.zabbix_templates)

        cls.devices = [
            create_test_device(name='Macro Assignment Test Device 1'),
            create_test_device(name='Macro Assignment Test Device 2'),
            create_test_device(name='Macro Assignment Test Device 3'),
            create_test_device(name='Macro Assignment Test Device 4'),
        ]
        cls.virtualmachines = [create_test_virtualmachine(name='VM1')]

        zabbixserver_ct = ContentType.objects.get_for_model(ZabbixServer)
        zabbixtemplate_ct = ContentType.objects.get_for_model(ZabbixTemplate)

        cls.device_ct = ContentType.objects.get_for_model(Device)
        cls.virtualmachine_ct = ContentType.objects.get_for_model(VirtualMachine)

        cls.zabbix_macros = [
            ZabbixMacro(macro='Zabbix Macro Bulk 1', value='Bulk Macro', description='Test Bulk Macro 1', hostmacroid=1, type=0, assigned_object_type=zabbixserver_ct, assigned_object_id=cls.zabbix_servers[0].id),
            ZabbixMacro(macro='Zabbix Macro Bulk 2', value='Bulk Macro', description='Test Bulk Macro 2', hostmacroid=2, type=0, assigned_object_type=zabbixtemplate_ct, assigned_object_id=cls.zabbix_templates[0].id),
        ]
        ZabbixMacro.objects.bulk_create(cls.zabbix_macros)

        zabbix_macroassignments = [
            ZabbixMacroAssignment(zabbixmacro=cls.zabbix_macros[0], value='demo', assigned_object_type=cls.device_ct, assigned_object_id=cls.devices[0].id),
            ZabbixMacroAssignment(zabbixmacro=cls.zabbix_macros[1], value='demo', assigned_object_type=cls.virtualmachine_ct, assigned_object_id=cls.virtualmachines[0].id),
        ]
        ZabbixMacroAssignment.objects.bulk_create(zabbix_macroassignments)

        cls.form_data = {'zabbixmacro': cls.zabbix_macros[1].id, 'is_regex': True, 'context': 'Bla', 'value': 'demo', 'device': cls.devices[0].id}

        cls.bulk_edit_data = {
            'value': 'Test Value 31',
        }

    def test_macroassignment_form_prefills_assigned_object(self):
        self.user.is_superuser = True
        self.user.save()

        url = reverse('plugins:nbxsync:zabbixmacroassignment_add')
        response = self.client.get(
            url,
            {
                'assigned_object_type': self.device_ct.pk,
                'assigned_object_id': self.devices[0].pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.devices[0].name)

        # Check that form initial includes the device prefilled
        html = response.content.decode().replace('\n', '').replace('  ', '')
        expected = f'value="{self.devices[0].pk}" selected'
        self.assertIn(expected, html)

    def test_clean_raises_if_multiple_assignments(self):
        form = ZabbixMacroAssignmentForm(
            data={
                'device': self.devices[0].pk,
                'virtualmachine': self.virtualmachines[0].pk,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('virtualmachine', form.errors)
        self.assertIn('A Macro can only be assigned to a single object.', form.errors['virtualmachine'][0])

    def test_macroassignment_form_invalid_content_type_triggers_prefill_exception(self):
        self.user.is_superuser = True
        self.user.save()

        # Use a clearly invalid content type ID
        invalid_ct_id = 99999  # unlikely to exist
        invalid_obj_id = 12345

        with self.assertLogs('nbxsync.forms', level='DEBUG') as cm:
            url = reverse('plugins:nbxsync:zabbixmacroassignment_add')
            response = self.client.get(url, {'assigned_object_type': invalid_ct_id, 'assigned_object_id': invalid_obj_id})
            self.assertEqual(response.status_code, 200)

        # Verify our except path executed and logged
        self.assertTrue(any('Prefill error' in msg for msg in cm.output))

    def test_clean_sets_assigned_object_none_if_unassigned(self):
        form = ZabbixMacroAssignmentForm(data={'zabbixmacro': str(self.zabbix_macros[0].id)})

        form.is_valid()

        # Should not raise and assigned_object should be None
        self.assertIsNone(form.instance.assigned_object)

    def _get_base_url(self):
        return 'plugins:nbxsync:zabbixmacroassignment_{}'
