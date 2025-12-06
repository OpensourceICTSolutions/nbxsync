from django.db.models import Q
from django_filters import CharFilter

from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixConfigurationGroup


__all__ = ('ZabbixConfigurationGroupFilterSet',)


class ZabbixConfigurationGroupFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')

    name = CharFilter(lookup_expr='icontains')
    description = CharFilter(lookup_expr='icontains')

    class Meta:
        model = ZabbixConfigurationGroup
        fields = ('id', 'name', 'description')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset

        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value)).distinct()
