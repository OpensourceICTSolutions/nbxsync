from django.db.models import Q
from django_filters import CharFilter, DateFromToRangeFilter, ModelMultipleChoiceFilter, MultipleChoiceFilter, NumberFilter

from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.choices import ZabbixTimePeriodDayofWeekChoices, ZabbixTimePeriodMonthChoices, ZabbixTimePeriodTypeChoices
from nbxsync.models import ZabbixMaintenance, ZabbixMaintenancePeriod


__all__ = ('ZabbixMaintenancePeriodFilterSet',)


class ZabbixMaintenancePeriodFilterSet(NetBoxModelFilterSet):
    # Free-text search
    q = CharFilter(method='search', label='Search')

    # Simple / numeric filters
    period = NumberFilter()
    every = NumberFilter()
    day = NumberFilter()

    # Choice filters
    timeperiod_type = MultipleChoiceFilter(choices=ZabbixTimePeriodTypeChoices)

    # ArrayField (int choices) — match ANY of the selected values using Postgres 'overlap'
    dayofweek = MultipleChoiceFilter(choices=ZabbixTimePeriodDayofWeekChoices, field_name='dayofweek', lookup_expr='overlap', label='Day(s) of week')
    month = MultipleChoiceFilter(choices=ZabbixTimePeriodMonthChoices, field_name='month', lookup_expr='overlap', label='Month(s)')

    # Foreign key filters (by ID and by name)
    zabbixmaintenance_id = ModelMultipleChoiceFilter(field_name='zabbixmaintenance', queryset=ZabbixMaintenance.objects.all(), label='Maintenance (ID)')
    zabbixmaintenance = ModelMultipleChoiceFilter(
        field_name='zabbixmaintenance__name',
        to_field_name='name',
        queryset=ZabbixMaintenance.objects.all(),
        label='Maintenance (name)',
    )

    # Date range (produces ?start_date_after=...&start_date_before=...)
    start_date = DateFromToRangeFilter(field_name='start_date', label='Start date (range)')

    # Numeric range helpers for start_time (seconds since midnight)
    start_time_min = NumberFilter(field_name='start_time', lookup_expr='gte', label='Start time ≥ (s)')
    start_time_max = NumberFilter(field_name='start_time', lookup_expr='lte', label='Start time ≤ (s)')

    class Meta:
        model = ZabbixMaintenancePeriod
        fields = (
            'id',
            'zabbixmaintenance_id',
            'zabbixmaintenance',
            'period',
            'timeperiod_type',
            'start_date',
            'start_time_min',
            'start_time_max',
            'every',
            'dayofweek',
            'day',
            'month',
        )

    def search(self, queryset, name, value):
        """
        Free-text search across useful fields:
        - Parent maintenance name
        - Numeric term checks: period, day, start_time exact match
        """
        term = (value or '').strip()
        if not term:
            return queryset

        q_obj = Q(zabbixmaintenance__name__icontains=term)

        if term.isdigit():
            num = int(term)
            q_obj |= Q(period=num) | Q(day=num) | Q(start_time=num)

        return queryset.filter(q_obj).distinct()
