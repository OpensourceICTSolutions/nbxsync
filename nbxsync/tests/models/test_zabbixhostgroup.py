from django.core.exceptions import ValidationError
from django.test import TestCase

from nbxsync.models import ZabbixHostgroup, ZabbixServer


class ZabbixHostgroupTestCase(TestCase):
    def setUp(self):
        self.zabbixserver = ZabbixServer.objects.create(name='Main Server', description='Main testing server', url='http://127.0.0.1', token='supersecrettoken', validate_certs=True)

        self.valid_data = {
            'zabbixserver': self.zabbixserver,
            'name': 'Linux Hosts',
            'groupid': 1001,
            'description': 'Group for Linux systems',
            'value': 'Some optional value',
        }

    def test_valid_hostgroup_creation(self):
        hostgroup = ZabbixHostgroup(**self.valid_data)
        hostgroup.full_clean()
        hostgroup.save()
        self.assertEqual(ZabbixHostgroup.objects.count(), 1)

    def test_missing_required_fields(self):
        required_fields = ['name', 'zabbixserver']
        for field in required_fields:
            data = self.valid_data.copy()
            data.pop(field)
            hostgroup = ZabbixHostgroup(**data)
            with self.assertRaises(ValidationError):
                hostgroup.full_clean()

    def test_optional_fields_can_be_blank(self):
        data = self.valid_data.copy()
        data['description'] = ''
        data['value'] = ''
        data['groupid'] = None
        hostgroup = ZabbixHostgroup(**data)
        hostgroup.full_clean()

    def test_name_uniqueness_per_zabbixserver(self):
        ZabbixHostgroup.objects.create(**self.valid_data)
        duplicate = ZabbixHostgroup(**self.valid_data)
        with self.assertRaises(ValidationError) as cm:
            duplicate.full_clean()
        self.assertIn('__all__', cm.exception.message_dict)
        self.assertIn('Hostgroup must be unique per Zabbix Server', cm.exception.message_dict['__all__'])

    def test_groupid_uniqueness_per_zabbixserver(self):
        ZabbixHostgroup.objects.create(**self.valid_data)
        new_data = self.valid_data.copy()
        new_data['name'] = 'Other Group'
        duplicate = ZabbixHostgroup(**new_data)
        with self.assertRaises(ValidationError) as cm:
            duplicate.full_clean()
        self.assertIn('__all__', cm.exception.message_dict)
        self.assertIn('Hostgroup ID must be unique per Zabbix Server', cm.exception.message_dict['__all__'])

    def test_str_method(self):
        hostgroup = ZabbixHostgroup.objects.create(**self.valid_data)
        result = str(hostgroup)
        expected = f'{hostgroup.name} ({hostgroup.zabbixserver.name})'
        self.assertEqual(result, expected)

    def test_uniqueness_constraints_with_different_servers(self):
        another_server = ZabbixServer.objects.create(name='Secondary Server', description='Second server', url='http://127.0.0.2', token='another-token', validate_certs=False)
        ZabbixHostgroup.objects.create(**self.valid_data)

        new_data = self.valid_data.copy()
        new_data['zabbixserver'] = another_server
        hostgroup = ZabbixHostgroup(**new_data)
        hostgroup.full_clean()  # Should not raise

    def test_is_template_true_when_value_contains_jinja(self):
        hostgroup = ZabbixHostgroup.objects.create(
            **{
                **self.valid_data,
                'value': 'Apply to {{ hostname }} only',
            }
        )
        self.assertTrue(hostgroup.is_template())

    def test_is_template_false_when_value_is_plain_text(self):
        hostgroup = ZabbixHostgroup.objects.create(
            **{
                **self.valid_data,
                'name': 'Plain Text Group',
                'groupid': 2002,
                'value': 'No templating here',
            }
        )
        self.assertFalse(hostgroup.is_template())
