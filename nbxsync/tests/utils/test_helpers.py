from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from nbxsync.choices import HostInterfaceRequirementChoices, ZabbixMacroTypeChoices
from nbxsync.models import ZabbixMacro, ZabbixServer, ZabbixTemplate
from nbxsync.utils.helpers import create_or_update_zabbixmacro, create_or_update_zabbixtemplate


class HelperTests(TestCase):
    def setUp(self):
        self.zabbixserver = ZabbixServer.objects.create(name='Zabbix Test', url='http://localhost', token='abc123')

    def test_create_new_template(self):
        data = {'templateid': 1234, 'name': 'Linux Template', 'interface_requirements': [HostInterfaceRequirementChoices.AGENT]}

        result = create_or_update_zabbixtemplate(data.copy(), self.zabbixserver)
        self.assertIsNotNone(result)
        self.assertEqual(result.templateid, 1234)
        self.assertEqual(result.name, 'Linux Template')
        self.assertEqual(result.zabbixserver, self.zabbixserver)

    def test_update_existing_template(self):
        template = ZabbixTemplate.objects.create(name='Old Name', templateid=4321, zabbixserver=self.zabbixserver, interface_requirements=[HostInterfaceRequirementChoices.SNMP])

        data = {'templateid': 4321, 'name': 'Updated Name'}

        updated = create_or_update_zabbixtemplate(data.copy(), self.zabbixserver)
        self.assertEqual(updated.id, template.id)
        self.assertEqual(updated.name, 'Updated Name')

    def test_update_existing_template_invalid_serializer(self):
        # Create a template that will match `templateid`
        template = ZabbixTemplate.objects.create(name='Invalid Update Template', templateid=321, zabbixserver=self.zabbixserver, interface_requirements=[])

        # Pass invalid data (e.g., name is too long)
        bad_data = {
            'templateid': 321,
            'name': 'x' * 600,  # Exceeds max_length=512
        }

        result = create_or_update_zabbixtemplate(bad_data.copy(), self.zabbixserver)

        # Should return the existing object unchanged
        self.assertEqual(result.id, template.id)
        # Also, verify that name didn't change
        template.refresh_from_db()
        self.assertEqual(template.name, 'Invalid Update Template')

    def test_create_new_template_invalid_serializer(self):
        bad_data = {'templateid': 9999, 'name': ''}

        result = create_or_update_zabbixtemplate(bad_data.copy(), self.zabbixserver)

        self.assertIsNone(result)
        self.assertFalse(ZabbixTemplate.objects.filter(templateid=9999).exists())

    def test_create_new_macro(self):
        template = ZabbixTemplate.objects.create(name='Macro Template', templateid=5555, zabbixserver=self.zabbixserver, interface_requirements=[])

        macro_data = {
            'hostmacroid': 999,
            'macro': '{$EXAMPLE}',
            'value': 'testval',
            'type': ZabbixMacroTypeChoices.TEXT,
        }

        macro = create_or_update_zabbixmacro(macro_data.copy(), template)

        self.assertIsNotNone(macro)
        self.assertEqual(macro.hostmacroid, 999)
        self.assertEqual(macro.macro, '{$EXAMPLE}')
        self.assertEqual(macro.assigned_object_id, template.id)
        self.assertEqual(macro.assigned_object_type, ContentType.objects.get_for_model(template))

    def test_update_existing_macro(self):
        template = ZabbixTemplate.objects.create(name='Update Macro Template', templateid=777, zabbixserver=self.zabbixserver, interface_requirements=[])
        macro = ZabbixMacro.objects.create(macro='{$TO_UPDATE}', value='old', type=ZabbixMacroTypeChoices.TEXT, hostmacroid=8888, assigned_object=template)

        macro_data = {'hostmacroid': 8888, 'macro': '{$TO_UPDATE}', 'value': 'new', 'type': ZabbixMacroTypeChoices.TEXT}

        updated_macro = create_or_update_zabbixmacro(macro_data.copy(), template)
        self.assertEqual(updated_macro.id, macro.id)
        self.assertEqual(updated_macro.value, 'new')

    def test_update_existing_macro_invalid_serializer(self):
        template = ZabbixTemplate.objects.create(name='Macro Update Template', templateid=888, zabbixserver=self.zabbixserver, interface_requirements=[])

        macro = ZabbixMacro.objects.create(macro='{$BROKEN}', value='oldvalue', type=ZabbixMacroTypeChoices.TEXT, hostmacroid=123, assigned_object=template)
        invalid_macro_data = {'hostmacroid': 123, 'macro': '', 'value': 'newvalue', 'type': ZabbixMacroTypeChoices.TEXT}

        result = create_or_update_zabbixmacro(invalid_macro_data.copy(), template)

        self.assertEqual(result.id, macro.id)
        self.assertEqual(result.value, 'oldvalue')  # Should not update due to invalid serializer

    def test_create_new_macro_invalid_serializer(self):
        template = ZabbixTemplate.objects.create(name='Macro Create Fail Template', templateid=999, zabbixserver=self.zabbixserver, interface_requirements=[])

        invalid_macro_data = {'hostmacroid': 999, 'macro': '', 'value': 'xyz', 'type': ZabbixMacroTypeChoices.TEXT}

        result = create_or_update_zabbixmacro(invalid_macro_data.copy(), template)

        self.assertIsNone(result)
        self.assertFalse(ZabbixMacro.objects.filter(hostmacroid=999).exists())
