from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from dcim.models import Device
from utilities.testing import ViewTestCases, create_test_device, create_test_virtualmachine

from nbxsync.choices import HostInterfaceRequirementChoices
from nbxsync.forms import ZabbixTemplateAssignmentForm
from nbxsync.models import ZabbixServer, ZabbixTemplate, ZabbixTemplateAssignment


class ZabbixTemplateAssignmentTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = ZabbixTemplateAssignment

    @classmethod
    def setUpTestData(cls):
        cls.devices = [
            create_test_device(name='Tag Assignment Test Device 1'),
            create_test_device(name='Tag Assignment Test Device 2'),
            create_test_device(name='Tag Assignment Test Device 3'),
            create_test_device(name='Tag Assignment Test Device 4'),
        ]
        cls.virtualmachines = [create_test_virtualmachine(name='VM1')]
        cls.device_ct = ContentType.objects.get_for_model(Device)
        cls.zabbixserver = [
            ZabbixServer.objects.create(
                name='Zabbix Server A',
                description='Test Server',
                url='http://example.com',
                token='dummy-token',
                validate_certs=True,
            ),
            ZabbixServer.objects.create(
                name='Zabbix Server B',
                description='Test Server',
                url='http://example_b.com',
                token='dummy-token',
                validate_certs=True,
            ),
        ]

        cls.zabbix_templates = [
            ZabbixTemplate(
                name='Template #1',
                zabbixserver=cls.zabbixserver[0],
                templateid=1,
                interface_requirements=[HostInterfaceRequirementChoices.AGENT, HostInterfaceRequirementChoices.ANY],
            ),
            ZabbixTemplate(
                name='Template #2',
                zabbixserver=cls.zabbixserver[0],
                templateid=2,
                interface_requirements=[HostInterfaceRequirementChoices.AGENT, HostInterfaceRequirementChoices.ANY],
            ),
            ZabbixTemplate(
                name='Template #3',
                zabbixserver=cls.zabbixserver[0],
                templateid=3,
                interface_requirements=[HostInterfaceRequirementChoices.AGENT, HostInterfaceRequirementChoices.ANY],
            ),
        ]
        ZabbixTemplate.objects.bulk_create(cls.zabbix_templates)

        zabbix_templateassignments = [
            ZabbixTemplateAssignment(
                zabbixtemplate=cls.zabbix_templates[0],
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[0].id,
            ),
            ZabbixTemplateAssignment(
                zabbixtemplate=cls.zabbix_templates[1],
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[1].id,
            ),
        ]
        ZabbixTemplateAssignment.objects.bulk_create(zabbix_templateassignments)

        cls.form_data = {'zabbixtemplate': cls.zabbix_templates[2].id, 'device': cls.devices[2].id}

    def test_templateassignment_form_prefills_assigned_object(self):
        self.user.is_superuser = True
        self.user.save()

        url = reverse('plugins:nbxsync:zabbixtemplateassignment_add')
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

    def test_templateassignment_form_invalid_content_type_triggers_prefill_log(self):
        self.user.is_superuser = True
        self.user.save()

        invalid_ct_id = 999999  # very unlikely to exist
        invalid_obj_id = 12345

        with self.assertLogs('nbxsync.forms', level='DEBUG') as cm:
            url = reverse('plugins:nbxsync:zabbixtemplateassignment_add')
            response = self.client.get(
                url,
                {'assigned_object_type': invalid_ct_id, 'assigned_object_id': invalid_obj_id},
            )
            self.assertEqual(response.status_code, 200)

        # Verify our except path executed and logged
        self.assertTrue(any('Prefill error' in msg for msg in cm.output))

    def test_clean_raises_if_multiple_assignments(self):
        form = ZabbixTemplateAssignmentForm(
            data={
                'device': self.devices[0].pk,
                'virtualmachine': self.virtualmachines[0].pk,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('virtualmachine', form.errors)
        self.assertIn('A Template can only be assigned to a single object.', form.errors['virtualmachine'][0])

    def test_clean_sets_assigned_object_none_if_unassigned(self):
        form = ZabbixTemplateAssignmentForm(data={'zabbixtemplate': str(self.zabbix_templates[0].id)})

        form.is_valid()

        # Should not raise and assigned_object should be None
        self.assertIsNone(form.instance.assigned_object)

    def _get_base_url(self):
        return 'plugins:nbxsync:zabbixtemplateassignment_{}'
