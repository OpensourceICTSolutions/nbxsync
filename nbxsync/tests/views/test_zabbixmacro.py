from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from dcim.models import Device
from utilities.testing import ViewTestCases, create_test_device

from nbxsync.forms import ZabbixMacroForm
from nbxsync.models import ZabbixMacro, ZabbixMacroAssignment, ZabbixServer, ZabbixTemplate


class ZabbixMacroTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ZabbixMacro

    @classmethod
    def setUpTestData(cls):
        cls.zabbix_servers = [
            ZabbixServer(
                name='Zabbix Server Bulk 1',
                description='Test Bulk Server 1',
                url='http://examplebulk1.com',
                token='bulk1-token',
                validate_certs=True,
            ),
            ZabbixServer(
                name='Zabbix Server Bulk 2',
                description='Test Bulk Server 2',
                url='http://examplebulk2.com',
                token='bulk2-token',
                validate_certs=True,
            ),
        ]
        ZabbixServer.objects.bulk_create(cls.zabbix_servers)

        cls.zabbix_templates = [
            ZabbixTemplate(name='Template 1', templateid=1, zabbixserver=cls.zabbix_servers[0], interface_requirements=[0]),
            ZabbixTemplate(name='Template 2', templateid=2, zabbixserver=cls.zabbix_servers[0], interface_requirements=[0]),
        ]
        ZabbixTemplate.objects.bulk_create(cls.zabbix_templates)

        cls.zabbixserver_ct = ContentType.objects.get_for_model(ZabbixServer)
        cls.zabbixtemplate_ct = ContentType.objects.get_for_model(ZabbixTemplate)

        zabbix_macros = [
            ZabbixMacro(
                macro='Zabbix Macro Bulk 1',
                value='Bulk Macro',
                description='Test Bulk Macro 1',
                hostmacroid=1,
                type=0,
                assigned_object_type=cls.zabbixserver_ct,
                assigned_object_id=cls.zabbix_servers[0].id,
            ),
            ZabbixMacro(
                macro='Zabbix Macro Bulk 2',
                value='Bulk Macro',
                description='Test Bulk Macro 2',
                hostmacroid=2,
                type=0,
                assigned_object_type=cls.zabbixtemplate_ct,
                assigned_object_id=cls.zabbix_templates[0].id,
            ),
        ]
        ZabbixMacro.objects.bulk_create(zabbix_macros)

        cls.form_data = {
            'macro': '{$Form Macro 1}',
            'value': 'Form Macro Value 1',
            'description': 'Form Description 1',
            'type': '1',
            'zabbixserver': cls.zabbix_servers[0].id,
        }

        cls.bulk_edit_data = {
            'description': 'Test Macro 31',
        }

    def test_macro_detail_view_includes_assignment_table_being_none(self):
        # Make the user superuser so we dont have to worry about *any* permissions
        self.user.is_superuser = True
        self.user.save()

        macro = ZabbixMacro.objects.all().first()
        url = self._get_detail_url(macro)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('objectassignment_table', response.context)

        table = response.context['objectassignment_table']
        self.assertIsNone(table)

    def test_macro_detail_view_includes_assignment_table(self):
        # Make the user superuser so we dont have to worry about *any* permissions
        self.user.is_superuser = True
        self.user.save()

        macro = ZabbixMacro.objects.all().first()
        device = create_test_device(name='Macro Assignment Test Device 1')
        device_ct = ContentType.objects.get_for_model(Device)

        zabbix_macroassignments = [
            ZabbixMacroAssignment(zabbixmacro=macro, value='demo', assigned_object_type=device_ct, assigned_object_id=device.id),
        ]
        ZabbixMacroAssignment.objects.bulk_create(zabbix_macroassignments)

        url = self._get_detail_url(macro)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('objectassignment_table', response.context)

        table = response.context['objectassignment_table']
        self.assertIsNotNone(table)
        self.assertGreater(len(table.rows), 0)

    def test_macro_form_prefills_assigned_object(self):
        self.user.is_superuser = True
        self.user.save()

        url = reverse('plugins:nbxsync:zabbixmacro_add')
        response = self.client.get(
            url,
            {
                'assigned_object_type': self.zabbixserver_ct.pk,
                'assigned_object_id': self.zabbix_servers[0].pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.zabbix_servers[0].name)

        # Check that form initial includes the device prefilled
        html = response.content.decode().replace('\n', '').replace('  ', '')
        expected = f'value="{self.zabbix_servers[0].pk}" selected'
        self.assertIn(expected, html)

    def test_macro_form_invalid_content_type_triggers_prefill_exception(self):
        self.user.is_superuser = True
        self.user.save()

        # Use a clearly invalid content type ID
        invalid_ct_id = 99999  # unlikely to exist
        invalid_obj_id = 12345

        with self.assertLogs('nbxsync.forms', level='DEBUG') as cm:
            url = reverse('plugins:nbxsync:zabbixmacro_add')
            response = self.client.get(
                url,
                {'assigned_object_type': invalid_ct_id, 'assigned_object_id': invalid_obj_id},
            )
            self.assertEqual(response.status_code, 200)

        # Verify our except path executed and logged
        self.assertTrue(any('Prefill error' in msg for msg in cm.output))

    def test_clean_raises_if_multiple_assignments(self):
        form = ZabbixMacroForm(
            data={
                'zabbixserver': self.zabbix_servers[0].pk,
                'zabbixtemplate': self.zabbix_templates[0].pk,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('zabbixtemplate', form.errors)
        self.assertIn('A Macro can only be assigned to a single object.', form.errors['zabbixtemplate'][0])

    def test_clean_sets_assigned_object_none_if_unassigned(self):
        form = ZabbixMacroForm(data={'value': 'bla'})

        form.is_valid()

        # Should not raise and assigned_object should be None
        self.assertIsNone(form.instance.assigned_object)

    def _get_base_url(self):
        return 'plugins:nbxsync:zabbixmacro_{}'

    def _get_detail_url(self, instance):
        return reverse('plugins:nbxsync:zabbixmacro', args=[instance.pk])
