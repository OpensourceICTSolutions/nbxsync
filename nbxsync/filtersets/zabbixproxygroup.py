from django.db.models import Q
from django_filters import CharFilter, ModelChoiceFilter, NumberFilter, OrderingFilter

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

    ordering = OrderingFilter(
        fields=(
            ('proxy_groupid', 'proxy_groupid'),
            ('name', 'name'),
            ('min_online', 'min_online'),
            ('failover_delay', 'failover_delay'),
            ('zabbixserver__name', 'zabbixserver_name'),
            ('id', 'id'),
        )
    )

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
