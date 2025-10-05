from django.db.models import Q
from django_filters import CharFilter

from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixServer


__all__ = ('ZabbixServerFilterSet',)


class ZabbixServerFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')

    name = CharFilter(lookup_expr='icontains')
    description = CharFilter(lookup_expr='icontains')
    url = CharFilter(lookup_expr='icontains')

    class Meta:
        model = ZabbixServer
        fields = (
            'id',
            'name',
            'description',
            'url',
            'token',
            'validate_certs',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value)).distinct()
