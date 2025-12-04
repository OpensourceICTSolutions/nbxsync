from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django_filters import CharFilter, ModelChoiceFilter, NumberFilter

from utilities.filters import ContentTypeFilter
from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixHostInterface


__all__ = ('ZabbixHostInterfaceFilterSet',)


class ZabbixHostInterfaceFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    zabbixserver_name = CharFilter(field_name='zabbixserver__name', lookup_expr='icontains')
    dns = CharFilter(lookup_expr='icontains')
    port = NumberFilter()
    snmp_community = CharFilter(lookup_expr='icontains')
    assigned_object_type = ContentTypeFilter()
    assigned_object_id = NumberFilter()

    class Meta:
        model = ZabbixHostInterface
        fields = (
            'id',
            'zabbixserver',
            'type',
            'interface_type',
            'useip',
            'dns',
            'port',
            'snmp_community',
            'ip',
            'assigned_object_type',
            'assigned_object_id',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(zabbixserver__name__icontains=value) | Q(dns__icontains=value)).distinct()
