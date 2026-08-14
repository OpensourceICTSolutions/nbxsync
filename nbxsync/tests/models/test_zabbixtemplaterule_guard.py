"""Tests for safe regex evaluation behind template rules.

Rule patterns are operator-supplied and matched against every synced platform
name. Evaluation must never raise, must reject nested-quantifier ReDoS shapes
at save time, and must not touch process-global signals (RQ job timeouts).
"""

import threading

from django.core.exceptions import ValidationError
from django.test import TestCase

from nbxsync.models import ZabbixHostgroup, ZabbixServer, ZabbixTemplate, ZabbixTemplateRule
from nbxsync.models.zabbixtemplaterule import _MAX_MATCH_INPUT


class TemplateRuleRegexGuardTestCase(TestCase):
    def setUp(self):
        self.server = ZabbixServer.objects.create(name='Guard Server', url='http://zabbix.local', token='abc123', validate_certs=True)
        self.template = ZabbixTemplate.objects.create(name='Linux by Zabbix agent', zabbixserver=self.server, templateid=10001)
        self.rule = ZabbixTemplateRule.objects.create(name='Linux', pattern='Ubuntu', zabbixtemplate=self.template)

    def test_matches_in_the_main_thread(self):
        self.assertTrue(self.rule.matches('Ubuntu 24.04 LTS'))
        self.assertFalse(self.rule.matches('Windows Server 2022'))

    def test_matches_from_a_worker_thread(self):
        results = []
        thread = threading.Thread(target=lambda: results.append(self.rule.matches('Ubuntu 24.04 LTS')))
        thread.start()
        thread.join()

        self.assertEqual(results, [True])

    def test_oversized_input_does_not_match(self):
        with self.assertLogs('nbxsync.models.zabbixtemplaterule', level='WARNING'):
            self.assertFalse(self.rule.matches('U' * (_MAX_MATCH_INPUT + 1)))

    def test_invalid_stored_pattern_does_not_match(self):
        ZabbixTemplateRule.objects.filter(pk=self.rule.pk).update(pattern='Windows (')
        self.rule.refresh_from_db()

        with self.assertLogs('nbxsync.models.zabbixtemplaterule', level='ERROR'):
            self.assertFalse(self.rule.matches('Windows Server 2022'))

    def test_invalid_pattern_is_rejected_on_save(self):
        rule = ZabbixTemplateRule(name='Broken', pattern='Windows (', zabbixtemplate=self.template)

        with self.assertRaises(ValidationError) as context:
            rule.full_clean()

        self.assertIn('pattern', context.exception.message_dict)

    def test_nested_quantifier_pattern_is_rejected_on_save(self):
        rule = ZabbixTemplateRule(name='ReDoS', pattern=r'(a+)+$', zabbixtemplate=self.template)

        with self.assertRaises(ValidationError) as context:
            rule.full_clean()

        self.assertIn('pattern', context.exception.message_dict)

    def test_hostgroup_must_share_the_template_server(self):
        other = ZabbixServer.objects.create(name='Other Server', url='http://other.local', token='xyz', validate_certs=True)
        foreign_group = ZabbixHostgroup.objects.create(name='Foreign', zabbixserver=other, groupid=42)
        rule = ZabbixTemplateRule(
            name='Cross-server',
            pattern='Ubuntu',
            zabbixtemplate=self.template,
            zabbixhostgroup=foreign_group,
        )

        with self.assertRaises(ValidationError) as context:
            rule.full_clean()

        self.assertIn('zabbixhostgroup', context.exception.message_dict)

    def test_hostgroup_on_same_server_is_accepted(self):
        group = ZabbixHostgroup.objects.create(name='Linux', zabbixserver=self.server, groupid=7)
        rule = ZabbixTemplateRule(
            name='Same-server',
            pattern='Ubuntu',
            zabbixtemplate=self.template,
            zabbixhostgroup=group,
        )

        rule.full_clean()  # must not raise
