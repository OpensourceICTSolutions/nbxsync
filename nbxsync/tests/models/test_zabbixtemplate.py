from django.core.exceptions import ValidationError
from django.test import TestCase

from nbxsync.choices import HostInterfaceRequirementChoices
from nbxsync.models import ZabbixServer, ZabbixTemplate
from nbxsync.models.zabbixtemplate import default_interfacerequirement


class ZabbixTemplateTestCase(TestCase):
    def setUp(self):
        self.zabbixserver1 = ZabbixServer.objects.create(name='Zabbix A', url='http://localhost', token='tokenA')
        self.zabbixserver2 = ZabbixServer.objects.create(name='Zabbix B', url='http://127.0.0.2', token='tokenB')
        self.valid_data = {'name': 'Linux OS Template', 'templateid': 12345, 'zabbixserver': self.zabbixserver1, 'interface_requirements': [HostInterfaceRequirementChoices.AGENT]}

    def test_valid_creation(self):
        template = ZabbixTemplate(**self.valid_data)
        template.full_clean()
        template.save()
        self.assertEqual(ZabbixTemplate.objects.count(), 1)
        self.assertEqual(template.interface_requirements, [HostInterfaceRequirementChoices.AGENT])

    def test_str_method(self):
        template = ZabbixTemplate.objects.create(**self.valid_data)
        self.assertEqual(str(template), f'{template.name} ({self.zabbixserver1.name})')

    def test_get_interface_requirements_display(self):
        template = ZabbixTemplate.objects.create(**self.valid_data)
        self.assertEqual(template.get_interface_requirements_display(), ['Agent'])

    def test_template_name_uniqueness_per_server(self):
        ZabbixTemplate.objects.create(**self.valid_data)

        data = self.valid_data.copy()
        data['templateid'] = 99999  # different ID
        with self.assertRaises(ValidationError) as cm:
            ZabbixTemplate(**data).full_clean()
        self.assertIn('Template name must be unique per Zabbix Server', str(cm.exception))

    def test_templateid_uniqueness_per_server(self):
        ZabbixTemplate.objects.create(**self.valid_data)

        data = self.valid_data.copy()
        data['name'] = 'Different Name'
        with self.assertRaises(ValidationError) as cm:
            ZabbixTemplate(**data).full_clean()
        self.assertIn('Template ID must be unique per Zabbix Server', str(cm.exception))

    def test_uniqueness_with_different_servers(self):
        ZabbixTemplate.objects.create(**self.valid_data)

        data = self.valid_data.copy()
        data['zabbixserver'] = self.zabbixserver2
        template = ZabbixTemplate(**data)
        template.full_clean()

    def test_default_interface_requirement_function(self):
        default = default_interfacerequirement()
        self.assertEqual(default, [HostInterfaceRequirementChoices.NONE.value])

    def test_default_interface_requirement_applied(self):
        data = self.valid_data.copy()
        data.pop('interface_requirements')

        template = ZabbixTemplate.objects.create(**data)
        self.assertEqual(template.interface_requirements, [HostInterfaceRequirementChoices.NONE.value])
