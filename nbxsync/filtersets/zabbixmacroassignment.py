from django.db.models import Q
from django_filters import BooleanFilter, CharFilter

from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixMacroAssignment

__all__ = ('ZabbixMacroAssignmentFilterSet',)


class ZabbixMacroAssignmentFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    zabbixmacro_macro = CharFilter(field_name='zabbixmacro__macro', lookup_expr='icontains')
    value = CharFilter(lookup_expr='icontains')
    context = CharFilter(lookup_expr='icontains')
    is_regex = BooleanFilter()

    class Meta:
        model = ZabbixMacroAssignment
        fields = (
            'id',
            'zabbixmacro',
            'is_regex',
            'context',
            'value',
            'zabbixmacro_macro',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(value__icontains=value) | Q(zabbixmacro__macro__icontains=value)).distinct()
