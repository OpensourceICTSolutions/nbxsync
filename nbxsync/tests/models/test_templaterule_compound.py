from django.db import models
from django.test import TestCase

from dcim.models import DeviceRole, Manufacturer
from extras.models import Tag as NetBoxTag
from utilities.testing import create_test_device

from nbxsync.models import ZabbixHostgroup, ZabbixServer, ZabbixTemplate, ZabbixTemplateRule
from nbxsync.utils.inheritance import get_assigned_zabbixobjects


class TemplateRuleCompoundCriteriaTestCase(TestCase):
    """Rule criteria are conjunctive: every configured criterion must match."""

    def setUp(self):
        self.server = ZabbixServer.objects.create(name='Criteria Zabbix', url='http://zabbix.local', token='abc123', validate_certs=True)
        self.template = ZabbixTemplate.objects.create(name='Rule Template', zabbixserver=self.server, templateid=42)
        self.tag = NetBoxTag.objects.create(name='critical', slug='critical')
        self.dell = Manufacturer.objects.create(name='Dell', slug='dell-criteria')
        self.hpe = Manufacturer.objects.create(name='HPE', slug='hpe-criteria')
        self.device = create_test_device(name='CompoundDev')

    def _rule(self, pattern='.*', role_pattern='', require_tags='', manufacturer=None):
        return ZabbixTemplateRule(
            name='test-rule',
            pattern=pattern,
            zabbixtemplate=self.template,
            role_pattern=role_pattern,
            require_tags=require_tags,
            manufacturer=manufacturer,
        )

    # --- matches() matrix ---

    def test_all_criteria_empty_matches_platform_only(self):
        rule = self._rule(pattern='Ubuntu')
        self.assertTrue(rule.matches('Ubuntu 22.04'))
        self.assertFalse(rule.matches('Windows'))

    def test_backward_compatible_single_arg_signature(self):
        rule = self._rule(pattern='Linux')
        self.assertTrue(rule.matches('Arch Linux'))

    def test_role_pattern_constrains(self):
        rule = self._rule(pattern='.*', role_pattern='^Switch')
        self.assertTrue(rule.matches('anything', role_name='Switch Core'))
        self.assertFalse(rule.matches('anything', role_name='Server'))

    def test_role_pattern_set_but_object_roleless_fails_closed(self):
        rule = self._rule(pattern='.*', role_pattern='^Switch')
        self.assertFalse(rule.matches('anything', role_name=None))

    def test_require_tags_all_must_be_present(self):
        rule = self._rule(pattern='.*', require_tags='critical,prod')
        self.assertTrue(rule.matches('x', netbox_tags={'critical', 'prod', 'extra'}))
        self.assertFalse(rule.matches('x', netbox_tags={'critical'}))
        self.assertFalse(rule.matches('x', netbox_tags=None))

    def test_manufacturer_match(self):
        rule = self._rule(pattern='.*', manufacturer=self.dell)
        self.assertTrue(rule.matches('x', manufacturer_id=self.dell.pk))
        self.assertFalse(rule.matches('x', manufacturer_id=self.hpe.pk))

    def test_manufacturer_set_but_object_without_manufacturer_fails_closed(self):
        rule = self._rule(pattern='.*', manufacturer=self.dell)
        self.assertFalse(rule.matches('x', manufacturer_id=None))

    def test_manufacturer_unset_is_wildcard(self):
        rule = self._rule(pattern='.*', manufacturer=None)
        self.assertTrue(rule.matches('x', manufacturer_id=self.dell.pk))
        self.assertTrue(rule.matches('x', manufacturer_id=None))

    def test_all_four_criteria_anded(self):
        rule = self._rule(pattern='Linux', role_pattern='^Server', require_tags='critical', manufacturer=self.dell)
        self.assertTrue(rule.matches('Ubuntu Linux', role_name='Server', netbox_tags={'critical'}, manufacturer_id=self.dell.pk))
        self.assertFalse(rule.matches('Windows', role_name='Server', netbox_tags={'critical'}, manufacturer_id=self.dell.pk))
        self.assertFalse(rule.matches('Ubuntu Linux', role_name='Switch', netbox_tags={'critical'}, manufacturer_id=self.dell.pk))
        self.assertFalse(rule.matches('Ubuntu Linux', role_name='Server', netbox_tags={'other'}, manufacturer_id=self.dell.pk))
        self.assertFalse(rule.matches('Ubuntu Linux', role_name='Server', netbox_tags={'critical'}, manufacturer_id=self.hpe.pk))

    def test_dell_and_server_without_tag(self):
        """Happy path for iDRAC: Dell ∧ Server, no NetBox tag required."""
        rule = self._rule(pattern='.*', role_pattern='^Server$', manufacturer=self.dell)
        self.assertTrue(rule.matches('Ubuntu', role_name='Server', manufacturer_id=self.dell.pk))
        self.assertFalse(rule.matches('Ubuntu', role_name='Server', manufacturer_id=self.hpe.pk))
        self.assertFalse(rule.matches('Ubuntu', role_name='Storage', manufacturer_id=self.dell.pk))

    def test_platformless_object_matches_catchall_only(self):
        self.assertTrue(self._rule(pattern='.*').matches(None))
        self.assertFalse(self._rule(pattern='Windows').matches(None))

    def test_disabled_or_garbage_never_raises_and_never_matches(self):
        r = self._rule(pattern='.*')
        r.enabled = False
        self.assertFalse(r.matches('Ubuntu'))


class TemplateRuleCompoundCriteriaCleanTestCase(TestCase):
    def test_role_pattern_nested_quantifier_rejected(self):
        from django.core.exceptions import ValidationError

        rule = ZabbixTemplateRule(name='bad', pattern='.*', role_pattern='(a+)+$', require_tags='')
        with self.assertRaises(ValidationError):
            rule.clean()

    def test_require_tags_rejects_non_slug(self):
        from django.core.exceptions import ValidationError

        rule = ZabbixTemplateRule(name='bad', pattern='.*', role_pattern='', require_tags='Critical!')
        with self.assertRaises(ValidationError):
            rule.clean()

    def test_manufacturer_protect_blocks_delete(self):
        server = ZabbixServer.objects.create(name='Protect Zabbix', url='http://zabbix.local', token='abc', validate_certs=True)
        template = ZabbixTemplate.objects.create(name='T', zabbixserver=server, templateid=99)
        mfr = Manufacturer.objects.create(name='ProtectMe', slug='protect-me')
        ZabbixTemplateRule.objects.create(name='scoped', pattern='.*', zabbixtemplate=template, manufacturer=mfr)
        with self.assertRaises(models.ProtectedError):
            mfr.delete()


class TemplateRuleCompoundResolutionTestCase(TestCase):
    """End-to-end through the resolver: criteria compound against the object."""

    def setUp(self):
        self.server = ZabbixServer.objects.create(name='Res Zabbix', url='http://zabbix.local', token='abc123', validate_certs=True)
        self.hostgroup = ZabbixHostgroup.objects.create(name='Rule Group', value='Rule Group', zabbixserver=self.server)
        self.template = ZabbixTemplate.objects.create(name='T', zabbixserver=self.server, templateid=43)
        self.tag = NetBoxTag.objects.create(name='critical', slug='critical')
        self.dell = Manufacturer.objects.create(name='Dell', slug='dell-resolve')
        self.hpe = Manufacturer.objects.create(name='HPE', slug='hpe-resolve')

    def test_rule_fires_only_when_all_criteria_match(self):
        rule = ZabbixTemplateRule.objects.create(
            name='combo',
            pattern='.*',
            zabbixtemplate=self.template,
            role_pattern=f'^{self.tag.slug[:2]}',
            require_tags=str(self.tag.slug),
        )
        # device role is 'Device Role' from create_test_device, platform None
        device = create_test_device(name='ComboDev')
        result = get_assigned_zabbixobjects(device)
        self.assertNotIn(rule.zabbixtemplate_id, [t.zabbixtemplate_id for t in result['templates']])

        # tag the device -> tag criterion still fails (role pattern does not match role name)
        device.tags.add(self.tag)
        result = get_assigned_zabbixobjects(device)
        self.assertNotIn(rule.zabbixtemplate_id, [t.zabbixtemplate_id for t in result['templates']])

        # role pattern that matches the test device's role + tag present -> fires
        rule.role_pattern = '.*'
        rule.save()
        result = get_assigned_zabbixobjects(device)
        self.assertIn(rule.zabbixtemplate_id, [t.zabbixtemplate_id for t in result['templates']])

    def test_manufacturer_and_role_resolution(self):
        """Dell ∧ Server links; HPE Server and Dell non-Server do not."""
        from dcim.models import DeviceType, Site

        server_role, _ = DeviceRole.objects.get_or_create(name='Server', defaults={'slug': 'server-mfr-rule'})
        storage_role, _ = DeviceRole.objects.get_or_create(name='Storage', defaults={'slug': 'storage-mfr-rule'})
        site = Site.objects.create(name='MfrRuleSite', slug='mfr-rule-site')
        dell_dt = DeviceType.objects.create(manufacturer=self.dell, model='PowerEdge R740', slug='poweredge-r740-mfr')
        hpe_dt = DeviceType.objects.create(manufacturer=self.hpe, model='ProLiant DL380', slug='proliant-dl380-mfr')
        dell_storage_dt = DeviceType.objects.create(manufacturer=self.dell, model='ME4 Storage', slug='me4-storage-mfr')

        rule = ZabbixTemplateRule.objects.create(
            name='Dell iDRAC',
            pattern='.*',
            role_pattern='^Server$',
            zabbixtemplate=self.template,
            manufacturer=self.dell,
            priority=80,
        )

        dell_server = create_test_device(name='DellServer')
        dell_server.device_type = dell_dt
        dell_server.role = server_role
        dell_server.site = site
        dell_server.save()

        hpe_server = create_test_device(name='HPEServer')
        hpe_server.device_type = hpe_dt
        hpe_server.role = server_role
        hpe_server.site = site
        hpe_server.save()

        dell_storage = create_test_device(name='DellStorage')
        dell_storage.device_type = dell_storage_dt
        dell_storage.role = storage_role
        dell_storage.site = site
        dell_storage.save()

        self.assertIn(rule.zabbixtemplate_id, [t.zabbixtemplate_id for t in get_assigned_zabbixobjects(dell_server)['templates']])
        self.assertNotIn(rule.zabbixtemplate_id, [t.zabbixtemplate_id for t in get_assigned_zabbixobjects(hpe_server)['templates']])
        self.assertNotIn(rule.zabbixtemplate_id, [t.zabbixtemplate_id for t in get_assigned_zabbixobjects(dell_storage)['templates']])

    def test_existing_rules_without_manufacturer_unchanged(self):
        rule = ZabbixTemplateRule.objects.create(name='platform-only', pattern='.*', zabbixtemplate=self.template)
        device = create_test_device(name='AnyMfr')
        result = get_assigned_zabbixobjects(device)
        self.assertIn(rule.zabbixtemplate_id, [t.zabbixtemplate_id for t in result['templates']])
