from django.db.models import Q
from django_filters import CharFilter

from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixMaintenanceTagAssignment

__all__ = ('ZabbixMaintenanceTagAssignmentFilterSet',)


class ZabbixMaintenanceTagAssignmentFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    zabbixmaintenance = CharFilter(field_name='zabbixmaintenance__name', lookup_expr='icontains')
    zabbixmaintenance_name = CharFilter(field_name='zabbixmaintenance__name', lookup_expr='icontains')

    class Meta:
        model = ZabbixMaintenanceTagAssignment
        fields = (
            'id',
            'zabbixmaintenance',
            'zabbixmaintenance_name',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(value__icontains=value) | Q(zabbixmaintenance_name__icontains=value)).distinct()
