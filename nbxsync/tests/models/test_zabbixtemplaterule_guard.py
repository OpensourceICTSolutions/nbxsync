"""Tests for the bounded regex evaluation behind template rules.

Rule patterns are operator-supplied and matched against every synced platform
name, so evaluation must be time-bounded and must never match when it cannot be
evaluated: linking a wrong template is worse than linking none.
"""

import threading
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from nbxsync.models import ZabbixServer, ZabbixTemplate, ZabbixTemplateRule
from nbxsync.models.zabbixtemplaterule import _MAX_MATCH_INPUT, _timed_regex_search


class TemplateRuleRegexGuardTestCase(TestCase):
    def setUp(self):
        server = ZabbixServer.objects.create(name='Guard Server', url='http://zabbix.local', token='abc123', validate_certs=True)
        self.template = ZabbixTemplate.objects.create(name='Linux by Zabbix agent', zabbixserver=server, templateid=10001)
        self.rule = ZabbixTemplateRule.objects.create(name='Linux', pattern='Ubuntu', zabbixtemplate=self.template)

    def test_matches_in_the_main_thread(self):
        self.assertTrue(self.rule.matches('Ubuntu 24.04 LTS'))
        self.assertFalse(self.rule.matches('Windows Server 2022'))

    def test_matches_from_a_worker_thread(self):
        """Signals cannot be installed off the main thread; matching still works."""
        results = []
        thread = threading.Thread(target=lambda: results.append(self.rule.matches('Ubuntu 24.04 LTS')))
        thread.start()
        thread.join()

        self.assertEqual(results, [True])

    def test_timeout_does_not_match(self):
        with patch('nbxsync.models.zabbixtemplaterule._timed_regex_search', side_effect=TimeoutError('boom')):
            with self.assertLogs('nbxsync.models.zabbixtemplaterule', level='WARNING') as logs:
                self.assertFalse(self.rule.matches('Ubuntu 24.04 LTS'))

        self.assertIn('Regex timeout', ' '.join(logs.output))

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

    def test_search_helper_reports_a_timeout(self):
        with patch('nbxsync.models.zabbixtemplaterule._search_with_signal', side_effect=ValueError('not main thread')):
            with patch('nbxsync.models.zabbixtemplaterule._compiled_pattern') as mock_compile:
                mock_compile.return_value.search.side_effect = lambda text: threading.Event().wait(5)
                with self.assertRaises(TimeoutError):
                    _timed_regex_search('Ubuntu', 'Ubuntu', timeout=1)
