from django.db.models import Q
from django_filters import CharFilter

from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixTemplateRule

__all__ = ('ZabbixTemplateRuleFilterSet',)


class ZabbixTemplateRuleFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    name = CharFilter(lookup_expr='icontains')
    description = CharFilter(lookup_expr='icontains')
    pattern = CharFilter(lookup_expr='icontains')

    class Meta:
        model = ZabbixTemplateRule
        fields = ('id', 'name', 'description', 'pattern', 'enabled', 'priority')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value) | Q(pattern__icontains=value)).distinct()
