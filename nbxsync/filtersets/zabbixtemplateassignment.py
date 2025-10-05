from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django_filters import CharFilter, ModelChoiceFilter, NumberFilter

from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixTemplate, ZabbixTemplateAssignment

__all__ = ('ZabbixTemplateAssignmentFilterSet',)


class ZabbixTemplateAssignmentFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    zabbixtemplate = ModelChoiceFilter(queryset=ZabbixTemplate.objects.all())
    zabbixtemplate_name = CharFilter(field_name='zabbixtemplate__name', lookup_expr='icontains')
    assigned_object_type = ModelChoiceFilter(queryset=ContentType.objects.all())
    assigned_object_id = NumberFilter()

    class Meta:
        model = ZabbixTemplateAssignment
        fields = (
            'id',
            'zabbixtemplate',
            'zabbixtemplate_name',
            'assigned_object_type',
            'assigned_object_id',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(zabbixtemplate__name__icontains=value)).distinct()
