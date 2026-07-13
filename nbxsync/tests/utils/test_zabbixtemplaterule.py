from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Platform
from utilities.testing import create_test_device

from nbxsync.models import ZabbixServer, ZabbixTemplate, ZabbixTemplateAssignment, ZabbixTemplateRule
from nbxsync.utils.inheritance import get_assigned_zabbixobjects


class ZabbixTemplateRuleTestCase(TestCase):
    def setUp(self):
        self.device = create_test_device(name='TestDev')
        self.server = ZabbixServer.objects.create(name='Zabbix1', url='http://zabbix.local', token='abc123', validate_certs=True)
        self.template_windows = ZabbixTemplate.objects.create(name='Windows by Zabbix agent', zabbixserver=self.server, templateid=10081)
        self.template_linux = ZabbixTemplate.objects.create(name='Linux by Zabbix agent', zabbixserver=self.server, templateid=10001)
        self.platform_ct = ContentType.objects.get_for_model(Platform)

    @patch('nbxsync.utils.inheritance.get_plugin_settings')
    def test_regex_rule_matches_platform_name(self, mock_settings):
        mock_settings.return_value.inheritance_chain = []
        platform = Platform.objects.create(name='Windows Server 2022 (Build 20348.5400)', slug='win-2022-5400')
        self.device.platform = platform
        self.device.save()

        ZabbixTemplateRule.objects.create(
            name='Windows',
            pattern='Windows',
            zabbixtemplate=self.template_windows,
        )

        result = get_assigned_zabbixobjects(self.device)

        templates = result['templates']
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0].zabbixtemplate, self.template_windows)

    @patch('nbxsync.utils.inheritance.get_plugin_settings')
    def test_regex_rule_does_not_match_wrong_platform(self, mock_settings):
        mock_settings.return_value.inheritance_chain = []
        platform = Platform.objects.create(name='Ubuntu 24.04 LTS', slug='ubuntu-2404')
        self.device.platform = platform
        self.device.save()

        ZabbixTemplateRule.objects.create(
            name='Windows',
            pattern='Windows',
            zabbixtemplate=self.template_windows,
        )

        result = get_assigned_zabbixobjects(self.device)

        self.assertEqual(result['templates'], [])

    @patch('nbxsync.utils.inheritance.get_plugin_settings')
    def test_multiple_rules_match_correctly(self, mock_settings):
        mock_settings.return_value.inheritance_chain = []
        win_platform = Platform.objects.create(name='Windows Server 2019', slug='win2019')
        linux_platform = Platform.objects.create(name='Ubuntu 22.04 LTS', slug='ubuntu2204')

        ZabbixTemplateRule.objects.create(name='Windows', pattern='Windows', zabbixtemplate=self.template_windows)
        ZabbixTemplateRule.objects.create(name='Linux', pattern='Ubuntu|Debian|Red Hat|CentOS', zabbixtemplate=self.template_linux)

        # Windows device
        self.device.platform = win_platform
        self.device.save()
        result = get_assigned_zabbixobjects(self.device)
        self.assertEqual(len(result['templates']), 1)
        self.assertEqual(result['templates'][0].zabbixtemplate, self.template_windows)

        # Linux device
        device2 = create_test_device(name='TestDev2')
        device2.platform = linux_platform
        device2.save()
        result2 = get_assigned_zabbixobjects(device2)
        self.assertEqual(len(result2['templates']), 1)
        self.assertEqual(result2['templates'][0].zabbixtemplate, self.template_linux)

    @patch('nbxsync.utils.inheritance.get_plugin_settings')
    def test_direct_assignment_overrides_regex_rule(self, mock_settings):
        mock_settings.return_value.inheritance_chain = []
        platform = Platform.objects.create(name='Windows Server 2022', slug='win2022')
        self.device.platform = platform
        self.device.save()

        # Direct assignment on the device
        ZabbixTemplateAssignment.objects.create(
            zabbixtemplate=self.template_linux,
            assigned_object_type=ContentType.objects.get_for_model(type(self.device)),
            assigned_object_id=self.device.pk,
        )

        # Regex rule that would match Windows
        ZabbixTemplateRule.objects.create(name='Windows', pattern='Windows', zabbixtemplate=self.template_windows)

        result = get_assigned_zabbixobjects(self.device)

        # Direct assignment (template_linux) + regex rule (template_windows)
        # Both should appear because they are different templates
        # but direct assignment prevents the SAME template from being added by regex
        templates = result['templates']
        self.assertEqual(len(templates), 2)
        template_ids = {t.zabbixtemplate_id for t in templates}
        self.assertEqual(template_ids, {self.template_linux.id, self.template_windows.id})

    @patch('nbxsync.utils.inheritance.get_plugin_settings')
    def test_disabled_rule_ignored(self, mock_settings):
        mock_settings.return_value.inheritance_chain = []
        platform = Platform.objects.create(name='Windows Server 2022', slug='win2022')
        self.device.platform = platform
        self.device.save()

        ZabbixTemplateRule.objects.create(
            name='Windows',
            pattern='Windows',
            zabbixtemplate=self.template_windows,
            enabled=False,
        )

        result = get_assigned_zabbixobjects(self.device)

        self.assertEqual(result['templates'], [])

    @patch('nbxsync.utils.inheritance.get_plugin_settings')
    def test_case_insensitive_matching(self, mock_settings):
        mock_settings.return_value.inheritance_chain = []
        platform = Platform.objects.create(name='UBUNTU 24.04 LTS', slug='ubuntu-2404')
        self.device.platform = platform
        self.device.save()

        ZabbixTemplateRule.objects.create(name='Linux', pattern='ubuntu', zabbixtemplate=self.template_linux)

        result = get_assigned_zabbixobjects(self.device)

        self.assertEqual(len(result['templates']), 1)
        self.assertEqual(result['templates'][0].zabbixtemplate, self.template_linux)

    @patch('nbxsync.utils.inheritance.get_plugin_settings')
    def test_device_without_platform_no_rules(self, mock_settings):
        mock_settings.return_value.inheritance_chain = []

        ZabbixTemplateRule.objects.create(name='Windows', pattern='Windows', zabbixtemplate=self.template_windows)

        result = get_assigned_zabbixobjects(self.device)

        self.assertEqual(result['templates'], [])

    @patch('nbxsync.utils.inheritance.get_plugin_settings')
    def test_rule_priority_ordering(self, mock_settings):
        mock_settings.return_value.inheritance_chain = []
        platform = Platform.objects.create(name='Windows Ubuntu Hybrid', slug='hybrid')
        self.device.platform = platform
        self.device.save()

        # Both rules match, but Windows has lower priority value (higher priority)
        ZabbixTemplateRule.objects.create(name='Linux', pattern='Ubuntu', zabbixtemplate=self.template_linux, priority=200)
        ZabbixTemplateRule.objects.create(name='Windows', pattern='Windows', zabbixtemplate=self.template_windows, priority=100)

        result = get_assigned_zabbixobjects(self.device)

        # Both should match (different templates)
        templates = result['templates']
        self.assertEqual(len(templates), 2)
        template_ids = {t.zabbixtemplate_id for t in templates}
        self.assertEqual(template_ids, {self.template_windows.id, self.template_linux.id})
