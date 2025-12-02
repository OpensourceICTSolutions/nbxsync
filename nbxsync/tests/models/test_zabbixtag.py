from django.core.exceptions import ValidationError
from django.test import TestCase

from nbxsync.models import ZabbixTag


class ZabbixTagTestCase(TestCase):
    def setUp(self):
        self.valid_data = {'name': 'Environment Tag', 'description': 'Tag for environment scope', 'tag': 'environment', 'value': 'production'}

    def test_valid_tag_creation(self):
        tag = ZabbixTag(**self.valid_data)
        tag.full_clean()
        tag.save()
        self.assertEqual(ZabbixTag.objects.count(), 1)

    def test_missing_required_fields(self):
        required_fields = ['name', 'tag']
        for field in required_fields:
            data = self.valid_data.copy()
            data.pop(field)
            tag = ZabbixTag(**data)
            with self.assertRaises(ValidationError):
                tag.full_clean()

    def test_optional_fields_blank(self):
        data = self.valid_data.copy()
        data['description'] = ''
        data['value'] = ''
        tag = ZabbixTag(**data)
        tag.full_clean()

    def test_str_method(self):
        tag = ZabbixTag.objects.create(**self.valid_data)
        expected = f'{tag.name} ({tag.tag})'
        self.assertEqual(str(tag), expected)

    def test_is_template_true(self):
        tag = ZabbixTag.objects.create(
            **{
                **self.valid_data,
                'name': 'Template Tag',
                'tag': 'templated',
                'value': 'for {{ hostname }}',
            }
        )
        self.assertTrue(tag.is_template())

    def test_is_template_false(self):
        tag = ZabbixTag.objects.create(
            **{
                **self.valid_data,
                'name': 'Non Template Tag',
                'tag': 'notemplated',
                'value': 'just a plain string',
            }
        )
        self.assertFalse(tag.is_template())

    def test_str_returns_expected_format(self):
        tag = ZabbixTag.objects.create(**self.valid_data)
        self.assertEqual(str(tag), f'{self.valid_data["name"]} ({self.valid_data["tag"]})')
