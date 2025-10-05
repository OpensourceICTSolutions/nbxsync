from django.db.models import Q
from django_filters import CharFilter

from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixMacro

__all__ = ('ZabbixMacroFilterSet',)


class ZabbixMacroFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    macro = CharFilter(lookup_expr='icontains')
    value = CharFilter(lookup_expr='icontains')
    description = CharFilter(lookup_expr='icontains')
    hostmacroid = CharFilter(lookup_expr='icontains')

    class Meta:
        model = ZabbixMacro
        fields = (
            'id',
            'macro',
            'value',
            'description',
            'type',
            'hostmacroid',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset

        return queryset.filter(Q(macro__icontains=value) | Q(hostmacroid__icontains=value)).distinct()
