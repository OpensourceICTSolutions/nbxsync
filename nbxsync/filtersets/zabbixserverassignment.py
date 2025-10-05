from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django_filters import CharFilter, ModelChoiceFilter, NumberFilter

from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixServerAssignment

__all__ = ('ZabbixServerAssignmentFilterSet',)


class ZabbixServerAssignmentFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    zabbixserver_name = CharFilter(field_name='zabbixserver__name', lookup_expr='icontains')
    zabbixproxy_name = CharFilter(field_name='zabbixproxy__name', lookup_expr='icontains')
    zabbixproxygroup_name = CharFilter(field_name='zabbixproxygroup__name', lookup_expr='icontains')
    assigned_object_type = ModelChoiceFilter(queryset=ContentType.objects.all())
    assigned_object_id = NumberFilter()

    class Meta:
        model = ZabbixServerAssignment
        fields = (
            'id',
            'zabbixserver_name',
            'zabbixproxy_name',
            'zabbixproxygroup_name',
            'assigned_object_type',
            'assigned_object_id',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(zabbixserver__name__icontains=value) | Q(zabbixproxy__name__icontains=value) | Q(zabbixproxygroup__name__icontains=value)).distinct()
