from django.core.exceptions import ValidationError
from django.test import TestCase

from nbxsync.models import ZabbixServer


class ZabbixServerTestCase(TestCase):
    def setUp(self):
        self.valid_data = {'name': 'Test Server', 'description': 'Test Description', 'url': 'http://127.0.0.1', 'token': 's3cr3t-t0ken', 'validate_certs': False}

    def test_valid_zabbixserver_creation(self):
        server = ZabbixServer(**self.valid_data)
        server.full_clean()  # Should not raise
        server.save()
        self.assertEqual(ZabbixServer.objects.count(), 1)

    def test_missing_required_fields(self):
        required_fields = ['name', 'url', 'token']
        for field in required_fields:
            data = self.valid_data.copy()
            data.pop(field)
            server = ZabbixServer(**data)
            with self.assertRaises(ValidationError):
                server.full_clean()

    def test_blank_description_is_valid(self):
        data = self.valid_data.copy()
        data['description'] = ''
        server = ZabbixServer(**data)
        server.full_clean()

    def test_name_uniqueness_constraint(self):
        ZabbixServer.objects.create(**self.valid_data)
        duplicate = ZabbixServer(**self.valid_data)

        with self.assertRaises(ValidationError) as cm:
            duplicate.full_clean()

        self.assertIn('__all__', cm.exception.message_dict)
        self.assertIn('The Zabbix Server name must be unique', cm.exception.message_dict['__all__'])

    def test_url_uniqueness_constraint(self):
        ZabbixServer.objects.create(**self.valid_data)
        new_data = self.valid_data.copy()
        new_data['name'] = 'Another Server'
        duplicate = ZabbixServer(**new_data)
        with self.assertRaises(ValidationError) as cm:
            duplicate.full_clean()
        self.assertIn('__all__', cm.exception.message_dict)
        self.assertIn('The Zabbix Server URL must be unique', cm.exception.message_dict['__all__'])

    def test_str_method_returns_name(self):
        server = ZabbixServer.objects.create(**self.valid_data)
        self.assertEqual(str(server), server.name)

    def test_validate_certs_defaults_true(self):
        data = self.valid_data.copy()
        data.pop('validate_certs')
        server = ZabbixServer(**data)
        server.full_clean()
        server.save()
        self.assertTrue(server.validate_certs)
