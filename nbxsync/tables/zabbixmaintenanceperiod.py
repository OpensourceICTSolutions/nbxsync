import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable

from nbxsync.models import ZabbixMaintenancePeriod


__all__ = ('ZabbixMaintenancePeriodTable', 'ZabbixMaintenancePeriodObjectViewTable')


class ZabbixMaintenancePeriodTable(NetBoxTable):
    zabbixmaintenance = tables.Column(linkify=True, verbose_name=_('Maintenance'))
    period = tables.Column(verbose_name=_('Period'))
    timeperiod_type = tables.Column(verbose_name=_('Type'))
    start_date = tables.DateColumn(verbose_name=_('Start date'))
    start_time = tables.Column(verbose_name=_('Start time'))
    every = tables.Column(verbose_name=_('Every'))
    dayofweek = tables.Column(verbose_name=_('Day(s) of week'))
    day = tables.Column(verbose_name=_('Day of month'))
    month = tables.Column(verbose_name=_('Month(s)'))

    class Meta(NetBoxTable.Meta):
        model = ZabbixMaintenancePeriod
        fields = (
            'pk',
            'zabbixmaintenance',
            'period',
            'timeperiod_type',
            'start_date',
            'start_time',
            'every',
            'dayofweek',
            'day',
            'month',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'zabbixmaintenance',
            'period',
            'timeperiod_type',
            'start_date',
            'start_time',
            'every',
        )

    #
    # Renderers
    #

    def render_timeperiod_type(self, value, record):
        # Show the human-readable label for the choice
        return record.get_timeperiod_type_display()

    def render_start_time(self, value):
        """
        Value is seconds since midnight (0–86400). Render as HH:MM.
        86400 will be shown as 24:00.
        """
        if value is None:
            return ''
        hours = int(value // 3600)
        minutes = int((value % 3600) // 60)
        return f'{hours:02d}:{minutes:02d}'

    def _render_array_choices(self, record, field_name, values):
        """
        Helper to render ArrayField of choices as comma-separated human labels.
        """
        if not values:
            return ''
        field = record._meta.get_field(field_name)
        # For ArrayField, the per-item choices live on base_field.choices
        choices_map = dict(getattr(field.base_field, 'choices', ()) or ())
        rendered = [str(choices_map.get(v, v)) for v in values]
        return ', '.join(rendered)

    def render_dayofweek(self, value, record):
        return self._render_array_choices(record, 'dayofweek', value)

    def render_month(self, value, record):
        return self._render_array_choices(record, 'month', value)

    def render_period(self, value):
        """
        Period is total seconds. Return a compact, human string:
        e.g. 60 -> '1 minute', 3600 -> '1 hour', 4620 -> '1 hour, 17 minutes',
            65 -> '1 minute, 5 seconds'.
        """
        if value is None:
            return ''
        total = int(value)

        days, rem = divmod(total, 86_400)  # 24*3600
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


class ZabbixMaintenancePeriodObjectViewTable(NetBoxTable):
    period = tables.Column(verbose_name=_('Period'))
    timeperiod_type = tables.Column(verbose_name=_('Type'))
    start_date = tables.DateColumn(verbose_name=_('Start date'))
    start_time = tables.Column(verbose_name=_('Start time'))
    every = tables.Column(verbose_name=_('Every'))
    dayofweek = tables.Column(verbose_name=_('Day(s) of week'))
    day = tables.Column(verbose_name=_('Day of month'))
    month = tables.Column(verbose_name=_('Month(s)'))

    class Meta(NetBoxTable.Meta):
        model = ZabbixMaintenancePeriod
        fields = (
            'pk',
            'period',
            'timeperiod_type',
            'start_date',
            'start_time',
            'every',
            'dayofweek',
            'day',
            'month',
            'created',
            'last_updated',
        )
        default_columns = (
            'pk',
            'period',
            'timeperiod_type',
            'start_date',
            'start_time',
            'every',
        )

    #
    # Renderers
    #

    def render_timeperiod_type(self, value, record):
        # Show the human-readable label for the choice
        return record.get_timeperiod_type_display()

    def render_start_time(self, value):
        """
        Value is seconds since midnight (0–86400). Render as HH:MM.
        86400 will be shown as 24:00.
        """
        if value is None:
            return ''
        hours = int(value // 3600)
        minutes = int((value % 3600) // 60)
        return f'{hours:02d}:{minutes:02d}'

    def _render_array_choices(self, record, field_name, values):
        """
        Helper to render ArrayField of choices as comma-separated human labels.
        """
        if not values:
            return ''
        field = record._meta.get_field(field_name)
        # For ArrayField, the per-item choices live on base_field.choices
        choices_map = dict(getattr(field.base_field, 'choices', ()) or ())
        rendered = [str(choices_map.get(v, v)) for v in values]
        return ', '.join(rendered)

    def render_dayofweek(self, value, record):
        return self._render_array_choices(record, 'dayofweek', value)

    def render_month(self, value, record):
        return self._render_array_choices(record, 'month', value)

    def render_period(self, value):
        """
        Period is total seconds. Return a compact, human string:
        e.g. 60 -> '1 minute', 3600 -> '1 hour', 4620 -> '1 hour, 17 minutes',
            65 -> '1 minute, 5 seconds'.
        """
        if value is None:
            return ''
        total = int(value)

        days, rem = divmod(total, 86_400)  # 24*3600
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
