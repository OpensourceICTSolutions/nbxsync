import logging
import re
import signal
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from functools import lru_cache

from django.core.exceptions import ValidationError
from django.db import models
from netbox.models import NetBoxModel

logger = logging.getLogger(__name__)

__all__ = ('ZabbixTemplateRule',)

_REGEX_TIMEOUT = 2  # seconds
_MAX_MATCH_INPUT = 200  # characters; Platform names are far shorter


@lru_cache(maxsize=256)
def _compiled_pattern(pattern):
    return re.compile(pattern, re.IGNORECASE)


def _search_with_signal(pattern, text, timeout):
    class _RegexTimeoutError(Exception):
        pass

    def _alarm_handler(signum, frame):
        raise _RegexTimeoutError()

    old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
    old_alarm = signal.alarm(0)
    try:
        signal.alarm(timeout)
        try:
            return _compiled_pattern(pattern).search(text)
        except _RegexTimeoutError:
            raise TimeoutError(f'Regex search timed out after {timeout}s')
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        if old_alarm:
            signal.alarm(old_alarm)


def _timed_regex_search(pattern, text, timeout=_REGEX_TIMEOUT):
    """Run a regex search that cannot run longer than *timeout* for the caller.

    In the main thread (RQ worker jobs, single-threaded WSGI) the search is
    interrupted with signal.alarm. Signals can only be installed from the main
    thread, so a threaded caller (e.g. a threaded WSGI worker rendering the
    inheritance preview) instead waits on the search in a worker thread and
    abandons it once the deadline passes. Either way the caller is never pinned
    by a pathological pattern, and a timeout raises TimeoutError.
    """
    try:
        return _search_with_signal(pattern, text, timeout)
    except ValueError:
        # Not the main thread: signal.signal() is unavailable.
        pass

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_compiled_pattern(pattern).search, text)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            future.cancel()
            raise TimeoutError(f'Regex search timed out after {timeout}s')
        finally:
            # Do not block shutdown on a search that is still running.
            executor.shutdown(wait=False, cancel_futures=True)


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
        """Whether this rule applies to *platform_name*.

        Never raises: a rule that cannot be evaluated must not abort a host
        sync, and it must not match either — silently linking the wrong
        template is worse than linking none.
        """
        if not platform_name or not self.enabled:
            return False
        if len(platform_name) > _MAX_MATCH_INPUT:
            logger.warning('Rule "%s" not evaluated: platform name exceeds %s characters', self.name, _MAX_MATCH_INPUT)
            return False
        try:
            match = _timed_regex_search(self.pattern, platform_name)
        except TimeoutError:
            logger.warning(
                'Regex timeout for rule "%s" pattern "%s" on "%s"',
                self.name,
                self.pattern,
                platform_name[:50],
            )
            return False
        except re.error as err:
            # Patterns are validated on save, but a rule may predate that
            # validation or have been written directly to the database.
            logger.error('Rule "%s" has an invalid pattern "%s": %s', self.name, self.pattern, err)
            return False
        return bool(match)

    def __str__(self):
        return f'{self.name} ({self.pattern})'
