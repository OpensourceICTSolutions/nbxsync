from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django_filters import CharFilter, ModelChoiceFilter, NumberFilter
from utilities.filters import ContentTypeFilter

from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixTagAssignment


__all__ = ('ZabbixTagAssignmentFilterSet',)


class ZabbixTagAssignmentFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    zabbixtag_name = CharFilter(field_name='zabbixtag__name', lookup_expr='icontains')
    zabbixtag_tag = CharFilter(field_name='zabbixtag__tag', lookup_expr='icontains')
    assigned_object_type = ContentTypeFilter()
    assigned_object_id = NumberFilter()

    class Meta:
        model = ZabbixTagAssignment
        fields = (
            'id',
            'zabbixtag',
            'zabbixtag_name',
            'zabbixtag_tag',
            'assigned_object_type',
            'assigned_object_id',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(zabbixtag__name__icontains=value) | Q(zabbixtag__tag__icontains=value)).distinct()
