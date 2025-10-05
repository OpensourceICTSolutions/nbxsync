from datetime import datetime, timezone

import django_tables2 as tables
from django_tables2.utils import A
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixEvent
from nbxsync.choices import SeverityChoices, severity_css

__all__ = ('ZabbixEventTable',)


class ZabbixEventTable(NetBoxTable):
    zabbixserver = tables.Column(accessor='zabbixserver.name', verbose_name=_('Zabbix Server'), linkify={'viewname': 'plugins:nbxsync:zabbixserver', 'args': [A('zabbixserver.pk')]})
    event = tables.Column(verbose_name=_('Name'))
    acknowledged = tables.Column(verbose_name=_('Acknowledged'))
    severity = tables.Column(verbose_name=_('Severity'))
    start_time = tables.Column(verbose_name=_('Start Time'))
    end_time = tables.Column(verbose_name=_('End Time'))
    duration = tables.Column(verbose_name=_('Duration'), empty_values=())
    opdata = tables.Column(verbose_name=_('Operational Data'))

    class Meta(NetBoxTable.Meta):
        model = ZabbixEvent
        fields = (
            'zabbixserver',
            'event',
            'opdata',
            'severity',
            'start_time',
            'end_time',
            'duration',
            'acknowledged',
        )
        default_columns = (
            'zabbixserver',
            'event',
            'opdata',
            'severity',
            'start_time',
            'end_time',
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

    def render_start_time(self, value):
        return datetime.fromtimestamp(int(value)).strftime('%Y-%m-%d %H:%M:%S')

    def render_end_time(self, value):
        return datetime.fromtimestamp(int(value)).strftime('%Y-%m-%d %H:%M:%S')

    def render_duration(self, value, record):
        """value is the epoch from accessor='clock'."""
        try:
            epoch = int(value)
        except (TypeError, ValueError):
            return '-'

        days, rem = divmod(epoch, 86_400)  # 24*3600
        hours, rem = divmod(rem, 3_600)
        minutes, seconds = divmod(rem, 60)

        parts = []
        if days:
            parts.append(f'{days}d')
        if hours:
            parts.append(f'{hours}h')
        if minutes:
            parts.append(f'{minutes}m')
        if seconds:
            parts.append(f'{seconds}s')

        # If everything was zero, show '0 seconds'
        return ', '.join(parts) if parts else '0 seconds'
