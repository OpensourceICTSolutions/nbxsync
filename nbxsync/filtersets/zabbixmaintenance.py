from django.db.models import Q
from django_filters import CharFilter, IsoDateTimeFromToRangeFilter, ModelMultipleChoiceFilter, MultipleChoiceFilter, NumberFilter

from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.choices import ZabbixMaintenanceTagsEvalChoices, ZabbixMaintenanceTypeChoices
from nbxsync.models import ZabbixMaintenance, ZabbixServer


__all__ = ('ZabbixMaintenanceFilterSet',)


class ZabbixMaintenanceFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    name = CharFilter(lookup_expr='icontains')
    description = CharFilter(lookup_expr='icontains')
    maintenanceid = NumberFilter()
    maintenance_type = MultipleChoiceFilter(choices=ZabbixMaintenanceTypeChoices)
    tags_evaltype = MultipleChoiceFilter(choices=ZabbixMaintenanceTagsEvalChoices)

    zabbixserver_id = ModelMultipleChoiceFilter(
        field_name='zabbixserver',
        queryset=ZabbixServer.objects.all(),
        label='Zabbix Server (ID)',
    )
    zabbixserver = ModelMultipleChoiceFilter(
        field_name='zabbixserver__name',
        to_field_name='name',
        queryset=ZabbixServer.objects.all(),
        label='Zabbix Server (name)',
    )

    active_since = IsoDateTimeFromToRangeFilter(field_name='active_since', label='Active since (range)')
    active_till = IsoDateTimeFromToRangeFilter(field_name='active_till', label='Active till (range)')

    class Meta:
        model = ZabbixMaintenance
        fields = (
            'id',
            'name',
            'description',
            'maintenanceid',
            'maintenance_type',
            'tags_evaltype',
            'zabbixserver_id',
            'zabbixserver',
            'active_since',
            'active_till',
        )

    def search(self, queryset, name, value):
        term = (value or '').strip()
        if not term:
            return queryset

        q_obj = Q(name__icontains=term) | Q(description__icontains=term) | Q(zabbixserver__name__icontains=term)

        # If the term looks numeric, also try maintenanceid exact match
        if term.isdigit():
            q_obj |= Q(maintenanceid=int(term))

        return queryset.filter(q_obj).distinct()
