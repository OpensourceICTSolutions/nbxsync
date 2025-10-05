from datetime import datetime, timezone

import django_tables2 as tables
from django_tables2.utils import A
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixProblem
from nbxsync.choices import SeverityChoices, severity_css

__all__ = ('ZabbixProblemTable',)


class ZabbixProblemTable(NetBoxTable):
    zabbixserver = tables.Column(accessor='zabbixserver.name', verbose_name=_('Zabbix Server'), linkify={'viewname': 'plugins:nbxsync:zabbixserver', 'args': [A('zabbixserver.pk')]})
    problem = tables.Column(verbose_name=_('Name'))
    acknowledged = tables.Column(verbose_name=_('Acknowledged'))
    severity = tables.Column(verbose_name=_('Severity'))
    clock = tables.Column(verbose_name=_('Active Since'))
    duration = tables.Column(verbose_name=_('Duration'), accessor='clock', empty_values=())
    opdata = tables.Column(verbose_name=_('Operational Data'))

    class Meta(NetBoxTable.Meta):
        model = ZabbixProblem
        fields = (
            'zabbixserver',
            'problem',
            'opdata',
            'severity',
            'clock',
            'duration',
            'acknowledged',
        )
        default_columns = (
            'zabbixserver',
            'problem',
            'opdataseverity',
            'clock',
            'duration',
            'acknowledged',
        )
        exclude = ('id',)

    def render_severity(self, value):
        member = SeverityChoices(int(value))
        return format_html(
            '<span class="badge text-bg-{}">{}</span>',
            severity_css(member),
            member.label,
        )

    def render_acknowledged(self, value):
        if int(value):
            return format_html(
                '<span class="badge text-bg-info">Yes</span>',
            )

        return format_html(
            '<span class="badge text-bg-danger">No</span>',
        )

    def render_clock(self, value):
        return datetime.fromtimestamp(int(value)).strftime('%Y-%m-%d %H:%M:%S')

    def render_duration(self, value, record):
        """value is the epoch from accessor='clock'."""
        try:
            epoch = int(value)
        except (TypeError, ValueError):
            return '-'

        clock_dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
        delta = datetime.now(tz=timezone.utc) - clock_dt

        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(rem, 60)

        parts = []
        if days:
            parts.append(f'{days}d')
        if hours or days:
            parts.append(f'{hours}h')
        if minutes or hours or days:
            parts.append(f'{minutes}m')
        parts.append(f'{seconds}s')

        return ' '.join(parts)
