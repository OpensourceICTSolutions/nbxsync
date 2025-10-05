from django.db.models import Q
from django_filters import CharFilter

from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixTag


__all__ = ('ZabbixTagFilterSet',)


class ZabbixTagFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    name = CharFilter(lookup_expr='icontains')
    description = CharFilter(lookup_expr='icontains')
    tag = CharFilter(lookup_expr='icontains')
    value = CharFilter(lookup_expr='icontains')

    class Meta:
        model = ZabbixTag
        fields = ('id', 'name', 'description', 'tag', 'value')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value) | Q(tag__icontains=value) | Q(value__icontains=value)).distinct()
