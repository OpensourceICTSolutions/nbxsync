from django.db.models import Q
from django_filters import CharFilter, ModelChoiceFilter, NumberFilter

from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixProxyGroup, ZabbixServer

__all__ = ('ZabbixProxyGroupFilterSet',)


class ZabbixProxyGroupFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')

    name = CharFilter(lookup_expr='icontains')
    proxy_groupid = NumberFilter()
    min_online = NumberFilter()
    failover_delay = NumberFilter()
    zabbixserver = ModelChoiceFilter(queryset=ZabbixServer.objects.all())

    ordering = ('proxy_groupid', 'name', 'min_online', 'failover_delay', 'zabbixserver__name', 'id')

    class Meta:
        model = ZabbixProxyGroup
        fields = (
            'id',
            'proxy_groupid',
            'name',
            'min_online',
            'failover_delay',
            'zabbixserver',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value)).distinct()
