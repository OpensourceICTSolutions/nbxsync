import re

from django.db.models import Q
from django_filters import BooleanFilter, CharFilter, NumberFilter

from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixHostgroup

TEMPLATE_PATTERN = re.compile(r'({{.*?}}|{%-?\s*.*?\s*-?%}|{#.*?#})')

__all__ = ('ZabbixHostgroupFilterSet',)


class ZabbixHostgroupFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    zabbixserver_name = CharFilter(field_name='zabbixserver__name', lookup_expr='icontains')

    name = CharFilter(lookup_expr='icontains')
    description = CharFilter(lookup_expr='icontains')
    value = CharFilter(lookup_expr='icontains')
    groupid = NumberFilter()
    is_template = BooleanFilter(method='filter_is_template')

    class Meta:
        model = ZabbixHostgroup
        fields = ('id', 'name', 'description', 'value', 'groupid', 'zabbixserver', 'zabbixserver_name', 'is_template')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        try:
            groupid = int(value)
        except ValueError:
            groupid = None

        q = Q(name__icontains=value) | Q(zabbixserver__name__icontains=value)
        if groupid is not None:
            q |= Q(groupid=groupid)

        return queryset.filter(q).distinct()

    def filter_is_template(self, queryset, name, value):
        """
        Filter by whether `value` contains Jinja2 patterns.
        """
        if value:
            return queryset.filter(value__regex=TEMPLATE_PATTERN.pattern)
        else:
            return queryset.exclude(value__regex=TEMPLATE_PATTERN.pattern)
