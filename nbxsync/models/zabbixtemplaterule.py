import logging
import re
import signal

from django.core.exceptions import ValidationError
from django.db import models
from netbox.models import NetBoxModel

logger = logging.getLogger(__name__)

__all__ = ('ZabbixTemplateRule',)

_REGEX_TIMEOUT = 2  # seconds


def _timed_regex_search(pattern, text, timeout=_REGEX_TIMEOUT):
    """Run re.search with a timeout via signal.alarm.

    Works in the main thread (Django views, RQ worker jobs).  If called from
    a sub-thread where signals are unavailable, falls back to an unbounded
    re.search — acceptable because platform names are short (<100 chars) and
    patterns are validated at model save time.
    """

    class _RegexTimeoutError(Exception):
        pass

    def _alarm_handler(signum, frame):
        raise _RegexTimeoutError()

    try:
        old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
    except ValueError:
        return re.search(pattern, text, re.IGNORECASE)

    old_alarm = signal.alarm(0)
    try:
        signal.alarm(timeout)
        try:
            return re.search(pattern, text, re.IGNORECASE)
        except _RegexTimeoutError:
            raise TimeoutError(f'Regex search timed out after {timeout}s')
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        if old_alarm:
            signal.alarm(old_alarm)


class ZabbixTemplateRule(NetBoxModel):
    name = models.CharField(max_length=100, blank=False)
    description = models.CharField(max_length=200, blank=True)
    pattern = models.CharField(max_length=500, blank=False, help_text='Regex pattern matched against Platform name')
    zabbixtemplate = models.ForeignKey(to='nbxsync.ZabbixTemplate', on_delete=models.CASCADE, related_name='zabbixtemplaterules')
    zabbixhostgroup = models.ForeignKey(to='nbxsync.ZabbixHostgroup', on_delete=models.SET_NULL, related_name='zabbixtemplaterules', blank=True, null=True, help_text='Optional hostgroup assigned when the rule matches')
    zabbixtag = models.ForeignKey(to='nbxsync.ZabbixTag', on_delete=models.SET_NULL, related_name='zabbixtemplaterules', blank=True, null=True, help_text='Optional tag assigned when the rule matches')
    enabled = models.BooleanField(default=True)
    priority = models.IntegerField(default=100, help_text='Lower value = higher priority')

    class Meta:
        verbose_name = 'Zabbix Template Rule'
        verbose_name_plural = 'Zabbix Template Rules'
        ordering = ('priority', 'name')

    def clean(self):
        super().clean()
        try:
            re.compile(self.pattern)
        except re.error as e:
            raise ValidationError({'pattern': f'Invalid regex: {e}'})

    def matches(self, platform_name):
        if not platform_name or not self.enabled:
            return False
        try:
            match = _timed_regex_search(self.pattern, platform_name)
        except TimeoutError:
            logger.warning(
                'Regex timeout for rule "%s" pattern "%s" on "%s"',
                self.name, self.pattern, platform_name[:50],
            )
            return False
        return bool(match)

    def __str__(self):
        return f'{self.name} ({self.pattern})'
