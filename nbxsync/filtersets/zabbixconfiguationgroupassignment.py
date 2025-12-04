from django.db.models import Q
from django_filters import CharFilter, NumberFilter

from utilities.filters import ContentTypeFilter
from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixConfigurationGroupAssignment

__all__ = ('ZabbixConfigurationGroupAssignmentFilterSet',)


class ZabbixConfigurationGroupAssignmentFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    zabbixconfigurationgroup_name = CharFilter(field_name='zabbixconfigurationgroup__name', lookup_expr='icontains')
    assigned_object_type = ContentTypeFilter()
    assigned_object_id = NumberFilter()

    class Meta:
        model = ZabbixConfigurationGroupAssignment
        fields = (
            'id',
            'zabbixconfigurationgroup',
            'zabbixconfigurationgroup_name',
            'assigned_object_type',
            'assigned_object_id',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(zabbixconfigurationgroup__name__icontains=value)).distinct()
