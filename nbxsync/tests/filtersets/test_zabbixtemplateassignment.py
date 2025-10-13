from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.choices import HostInterfaceRequirementChoices
from nbxsync.filtersets import ZabbixTemplateAssignmentFilterSet
from nbxsync.models import ZabbixServer, ZabbixTemplate, ZabbixTemplateAssignment


class ZabbixTemplateAssignmentFilterSetTestCase(TestCase):
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

        cls.templates = [
            ZabbixTemplate.objects.create(
                name='Template #1',
                zabbixserver=cls.zabbixserver[0],
                templateid=1,
                interface_requirements=[HostInterfaceRequirementChoices.AGENT, HostInterfaceRequirementChoices.ANY],
            ),
            ZabbixTemplate.objects.create(
                name='Template #2',
                zabbixserver=cls.zabbixserver[1],
                templateid=2,
                interface_requirements=[HostInterfaceRequirementChoices.AGENT, HostInterfaceRequirementChoices.ANY],
            ),
        ]

        cls.devices = [
            create_test_device(name='Zabbix Device 1'),
            create_test_device(name='Zabbix Device 2'),
        ]

        cls.device_ct = ContentType.objects.get_for_model(Device)

        cls.assignments = [
            ZabbixTemplateAssignment.objects.create(
                zabbixtemplate=cls.templates[0],
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[0].id,
            ),
            ZabbixTemplateAssignment.objects.create(
                zabbixtemplate=cls.templates[1],
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[1].id,
            ),
        ]

    def test_search_by_template_name(self):
        f = ZabbixTemplateAssignmentFilterSet({'q': 'Template #1'}, queryset=ZabbixTemplateAssignment.objects.all())
        self.assertIn(self.assignments[0], f.qs)
        self.assertNotIn(self.assignments[1], f.qs)

    def test_search_blank_returns_all(self):
        queryset = ZabbixTemplateAssignment.objects.all()
        f = ZabbixTemplateAssignmentFilterSet({'q': ''}, queryset=queryset)
        self.assertQuerySetEqual(f.qs.order_by('id'), queryset.order_by('id'), transform=lambda x: x)

    def test_direct_search_method_blank(self):
        queryset = ZabbixTemplateAssignment.objects.all()
        f = ZabbixTemplateAssignmentFilterSet({}, queryset=queryset)
        result = f.search(queryset, name='q', value='   ')
        self.assertQuerySetEqual(result.order_by('id'), queryset.order_by('id'), transform=lambda x: x)

    def test_filter_by_zabbixtemplate_name(self):
        f = ZabbixTemplateAssignmentFilterSet({'zabbixtemplate_name': 'Template #2'}, queryset=ZabbixTemplateAssignment.objects.all())
        self.assertIn(self.assignments[1], f.qs)
        self.assertNotIn(self.assignments[0], f.qs)

    def test_filter_by_assigned_object_type(self):
        f = ZabbixTemplateAssignmentFilterSet({'assigned_object_type': f'{self.device_ct.app_label}.{self.device_ct.model}'}, queryset=ZabbixTemplateAssignment.objects.all())
        self.assertQuerySetEqual(f.qs.order_by('id'), ZabbixTemplateAssignment.objects.all().order_by('id'), transform=lambda x: x)

    def test_filter_by_assigned_object_id_only(self):
        f = ZabbixTemplateAssignmentFilterSet({'assigned_object_id': self.devices[0].id}, queryset=ZabbixTemplateAssignment.objects.all())
        self.assertIn(self.assignments[0], f.qs)
        self.assertNotIn(self.assignments[1], f.qs)

    def test_filter_by_type_and_id(self):
        f = ZabbixTemplateAssignmentFilterSet(
            {'assigned_object_type': f'{self.device_ct.app_label}.{self.device_ct.model}', 'assigned_object_id': self.devices[1].id},
            queryset=ZabbixTemplateAssignment.objects.all(),
        )
        self.assertIn(self.assignments[1], f.qs)
        self.assertNotIn(self.assignments[0], f.qs)

    def test_filter_fails_with_wrong_content_type(self):
        wrong_ct = ContentType.objects.get_for_model(ZabbixTemplate)
        f = ZabbixTemplateAssignmentFilterSet(
            {'assigned_object_type': f'{wrong_ct.app_label}.{wrong_ct.model}', 'assigned_object_id': self.devices[0].id},
            queryset=ZabbixTemplateAssignment.objects.all(),
        )
        self.assertEqual(f.qs.count(), 0)
