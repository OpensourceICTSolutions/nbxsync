from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from dcim.models import Device
from utilities.testing import ViewTestCases, create_test_device

from nbxsync.choices import HostInterfaceRequirementChoices
from nbxsync.forms import ZabbixTemplateBulkEditForm
from nbxsync.models import ZabbixMacro, ZabbixServer, ZabbixTemplate, ZabbixTemplateAssignment


class ZabbixTemplateTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ZabbixTemplate

    @classmethod
    def setUpTestData(cls):
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

        cls.form_data = {
            'name': 'Proxy X',
            'zabbixserver': cls.zabbixserver[0].id,
            'templateid': 4,
            'interface_requirements': [HostInterfaceRequirementChoices.AGENT, HostInterfaceRequirementChoices.ANY],
        }

        cls.bulk_edit_data = {
            'zabbixserver': cls.zabbixserver[1].id,
        }

    def test_templateassignment_detail_view_includes_assignment_table_being_none(self):
        # Make the user superuser so we dont have to worry about *any* permissions
        self.user.is_superuser = True
        self.user.save()

        url = self._get_detail_url(self.zabbix_templates[0])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('objectassignment_table', response.context)

        table = response.context['objectassignment_table']
        self.assertIsNone(table)

    def test_zabbixtemplate_detail_view_includes_assignment_table(self):
        # Make the user superuser so we dont have to worry about *any* permissions
        self.user.is_superuser = True
        self.user.save()

        template = ZabbixTemplate.objects.all().first()
        device = create_test_device(name='Zabbix Template Assignment Test Device 1')
        device_ct = ContentType.objects.get_for_model(Device)

        zabbix_templateassignments = [
            ZabbixTemplateAssignment(zabbixtemplate=template, assigned_object_type=device_ct, assigned_object_id=device.id),
        ]
        ZabbixTemplateAssignment.objects.bulk_create(zabbix_templateassignments)

        url = self._get_detail_url(template)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('objectassignment_table', response.context)

        table = response.context['objectassignment_table']
        self.assertIsNotNone(table)
        self.assertGreater(len(table.rows), 0)

    def test_zabbixtemplate_macros_view(self):
        # Make the user a superuser to skip permission checks
        self.user.is_superuser = True
        self.user.save()

        # Create a ZabbixTemplate
        template = ZabbixTemplate.objects.create(name='My Template', templateid=111, zabbixserver=self.zabbixserver[0], interface_requirements=[0])

        template_ct = ContentType.objects.get_for_model(ZabbixTemplate)

        # Macro assigned to this template
        macro_1 = ZabbixMacro.objects.create(
            macro='{$MACRO1}',
            value='value1',
            description='Test Macro 1',
            type=0,
            hostmacroid=1,
            assigned_object_type=template_ct,
            assigned_object_id=template.id,
        )

        # Unrelated macro assigned elsewhere
        macro_2 = ZabbixMacro.objects.create(
            macro='{$MACRO2}',
            value='value2',
            description='Unrelated',
            type=0,
            hostmacroid=2,
            assigned_object_type=template_ct,
            assigned_object_id=999999,  # Not this template
        )

        # Request the custom tab view
        url = reverse('plugins:nbxsync:zabbixtemplate_macros', args=[template.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('{$MACRO1}', content)
        self.assertNotIn('{$MACRO2}', content)

    def test_bulkedit_form_applies_default_interface_requirements(self):
        form = ZabbixTemplateBulkEditForm(data={'pk': [self.zabbix_templates[0].pk], 'zabbixserver': self.zabbixserver[0].pk})
        print(form.errors)
        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data['interface_requirements'],
            [HostInterfaceRequirementChoices.NONE],
        )

    def _get_base_url(self):
        return 'plugins:nbxsync:zabbixtemplate_{}'

    def _get_detail_url(self, instance):
        return reverse('plugins:nbxsync:zabbixtemplate', args=[instance.pk])
