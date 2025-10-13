from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django_filters import CharFilter, ModelChoiceFilter, NumberFilter

from utilities.filters import ContentTypeFilter
from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixHostgroupAssignment

__all__ = ('ZabbixHostgroupAssignmentFilterSet',)


class ZabbixHostgroupAssignmentFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    zabbixhostgroup_name = CharFilter(field_name='zabbixhostgroup__name', lookup_expr='icontains')
    value = CharFilter(lookup_expr='icontains')
    assigned_object_type = ContentTypeFilter()
    assigned_object_id = NumberFilter()

    class Meta:
        model = ZabbixHostgroupAssignment
        fields = (
            'id',
            'zabbixhostgroup',
            'zabbixhostgroup_name',
            'value',
            'assigned_object_type',
            'assigned_object_id',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(zabbixhostgroup__name__icontains=value)).distinct()
