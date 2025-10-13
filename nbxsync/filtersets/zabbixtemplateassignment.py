from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django_filters import CharFilter, ModelChoiceFilter, NumberFilter

from utilities.filters import ContentTypeFilter
from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixTemplate, ZabbixTemplateAssignment

__all__ = ('ZabbixTemplateAssignmentFilterSet',)


class ZabbixTemplateAssignmentFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    zabbixtemplate = ModelChoiceFilter(queryset=ZabbixTemplate.objects.all())
    zabbixtemplate_name = CharFilter(field_name='zabbixtemplate__name', lookup_expr='icontains')
    zabbixtemplate_id = NumberFilter(field_name='zabbixtemplate__templateid')
    assigned_object_type = ContentTypeFilter()
    assigned_object_id = NumberFilter()

    class Meta:
        model = ZabbixTemplateAssignment
        fields = (
            'id',
            'zabbixtemplate',
            'zabbixtemplate_name',
            'zabbixtemplate_id',
            'assigned_object_type',
            'assigned_object_id',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(zabbixtemplate__name__icontains=value)).distinct()
