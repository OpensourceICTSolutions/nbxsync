from django.db.models import Q
from django_filters import CharFilter, NumberFilter

from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixTemplate

__all__ = ('ZabbixTemplateFilterSet',)


class ZabbixTemplateFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    name = CharFilter(lookup_expr='icontains')
    templateid = NumberFilter()
    zabbixserver_name = CharFilter(field_name='zabbixserver__name', lookup_expr='icontains')

    class Meta:
        model = ZabbixTemplate
        fields = (
            'id',
            'name',
            'templateid',
            'zabbixserver',
            'zabbixserver_name',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(templateid__icontains=value) | Q(zabbixserver__name__icontains=value)).distinct()
