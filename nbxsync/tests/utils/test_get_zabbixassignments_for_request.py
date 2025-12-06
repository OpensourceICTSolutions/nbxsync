from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase

from utilities.testing import create_test_user, create_test_virtualmachine

from nbxsync.models import ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixMacro, ZabbixMacroAssignment, ZabbixServer, ZabbixTag, ZabbixTagAssignment, ZabbixTemplate, ZabbixTemplateAssignment
from nbxsync.tables import ZabbixHostgroupAssignmentObjectViewTable, ZabbixMacroAssignmentObjectViewTable, ZabbixTagAssignmentObjectViewTable, ZabbixTemplateAssignmentObjectViewTable
from nbxsync.utils.inheritance import get_zabbixassignments_for_request


class GetZabbixAssignmentsContextTestCase(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.user.is_superuser = True
        self.user.save()
        self.request = RequestFactory().get('/')
        self.request.user = self.user

        self.vm = create_test_virtualmachine(name='TestVM')
        self.ct = ContentType.objects.get_for_model(self.vm)

        self.server = ZabbixServer.objects.create(name='Zabbix1', url='http://zabbix.local', token='abc123', validate_certs=True)
        self.template = ZabbixTemplate.objects.create(name='Template OS', zabbixserver=self.server, templateid=101)
        self.macro = ZabbixMacro.objects.create(macro='{$USER}', value='admin', type=1, hostmacroid='901')
        self.tag = ZabbixTag.objects.create(tag='env', value='prod')
        self.hostgroup = ZabbixHostgroup.objects.create(name='Prod Group', value='prod-group', groupid=301, zabbixserver=self.server)
        self.template_assignment = ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=self.ct, assigned_object_id=self.vm.id)
        self.macro_assignment = ZabbixMacroAssignment.objects.create(zabbixmacro=self.macro, assigned_object_type=self.ct, assigned_object_id=self.vm.id, value='macro-value')
        self.tag_assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.ct, assigned_object_id=self.vm.id)
        self.group_assignment = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.ct, assigned_object_id=self.vm.id)

    def test_zabbixassignment_context(self):
        context = get_zabbixassignments_for_request(self.vm, self.request)

        # Assert presence of expected context keys
        self.assertIn('zabbix_template_table', context)
        self.assertIn('zabbix_macro_table', context)
        self.assertIn('zabbix_tag_table', context)
        self.assertIn('zabbix_hostgroup_table', context)

        self.assertIn('object', context)
        self.assertIn('content_type', context)

        # Assert correct instance & content type
        self.assertEqual(context['object'], self.vm)
        self.assertEqual(context['content_type'], self.ct)

        # Assert table classes and rows
        self.assertIsInstance(context['zabbix_template_table'], ZabbixTemplateAssignmentObjectViewTable)
        self.assertIsInstance(context['zabbix_macro_table'], ZabbixMacroAssignmentObjectViewTable)
        self.assertIsInstance(context['zabbix_tag_table'], ZabbixTagAssignmentObjectViewTable)
        self.assertIsInstance(context['zabbix_hostgroup_table'], ZabbixHostgroupAssignmentObjectViewTable)

        self.assertEqual(len(context['zabbix_template_table'].data), 1)
        self.assertEqual(len(context['zabbix_macro_table'].data), 1)
        self.assertEqual(len(context['zabbix_tag_table'].data), 1)
        self.assertEqual(len(context['zabbix_hostgroup_table'].data), 1)

    def test_zabbixassignment_context_empty(self):
        # Clean up all assignments
        ZabbixTemplateAssignment.objects.all().delete()
        ZabbixMacroAssignment.objects.all().delete()
        ZabbixTagAssignment.objects.all().delete()
        ZabbixHostgroupAssignment.objects.all().delete()

        context = get_zabbixassignments_for_request(self.vm, self.request)

        self.assertIsNone(context['zabbix_template_table'])
        self.assertIsNone(context['zabbix_macro_table'])
        self.assertIsNone(context['zabbix_tag_table'])
        self.assertIsNone(context['zabbix_hostgroup_table'])
