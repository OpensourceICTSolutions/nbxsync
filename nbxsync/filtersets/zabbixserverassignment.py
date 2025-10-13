from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django_filters import CharFilter, ModelChoiceFilter, NumberFilter

from netbox.filtersets import NetBoxModelFilterSet
from utilities.filters import ContentTypeFilter

from nbxsync.models import ZabbixServerAssignment

__all__ = ('ZabbixServerAssignmentFilterSet',)


class ZabbixServerAssignmentFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    zabbixserver_name = CharFilter(field_name='zabbixserver__name', lookup_expr='icontains')
    zabbixproxy_name = CharFilter(field_name='zabbixproxy__name', lookup_expr='icontains')
    zabbixproxy_id = NumberFilter(field_name='zabbixproxy__proxyid')
    zabbixproxygroup_name = CharFilter(field_name='zabbixproxygroup__name', lookup_expr='icontains')
    assigned_object_type = ContentTypeFilter()
    assigned_object_id = NumberFilter()
    hostid = NumberFilter()

    class Meta:
        model = ZabbixServerAssignment
        fields = (
            'id',
            'hostid',
            'zabbixserver_name',
            'zabbixproxy_name',
            'zabbixproxy_id',
            'zabbixproxygroup_name',
            'assigned_object_type',
            'assigned_object_id',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        try:
            hostid = int(value)
        except ValueError:
            hostid = None

        q = Q(zabbixserver__name__icontains=value) | Q(zabbixproxy__name__icontains=value) | Q(zabbixproxygroup__name__icontains=value)
        if hostid is not None:
            q |= Q(hostid=hostid)

        return queryset.filter(q).distinct()
