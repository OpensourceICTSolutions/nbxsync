from django.db.models import Q
from django_filters import CharFilter, ModelChoiceFilter, NumberFilter

from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixProxy, ZabbixServer

__all__ = ('ZabbixProxyFilterSet',)


class ZabbixProxyFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    name = CharFilter(lookup_expr='icontains')
    proxygroup_name = CharFilter(field_name='proxygroup__name', lookup_expr='icontains', required=False)
    proxygroup = ModelChoiceFilter(field_name='proxygroup', queryset=ZabbixProxy.objects.all(), required=False)
    proxygroup_id = NumberFilter(field_name='proxygroup__proxy_groupid')
    zabbixserver = ModelChoiceFilter(field_name='zabbixserver', queryset=ZabbixServer.objects.all(), required=False)

    class Meta:
        model = ZabbixProxy
        fields = (
            'id',
            'name',
            'zabbixserver',
            'proxyid',
            'proxygroup_id',
            'operating_mode',
            'address',
            'port',
            'tls_connect',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(address__icontains=value) | Q(local_address__icontains=value)).distinct()
