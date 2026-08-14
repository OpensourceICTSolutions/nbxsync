from django.db.models import Q
from django_filters import CharFilter, ModelMultipleChoiceFilter

from dcim.models import Manufacturer
from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixTemplateRule

__all__ = ('ZabbixTemplateRuleFilterSet',)


class ZabbixTemplateRuleFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')
    name = CharFilter(lookup_expr='icontains')
    description = CharFilter(lookup_expr='icontains')
    pattern = CharFilter(lookup_expr='icontains')
    role_pattern = CharFilter(lookup_expr='icontains')
    require_tags = CharFilter(lookup_expr='icontains')
    manufacturer_id = ModelMultipleChoiceFilter(
        field_name='manufacturer',
        queryset=Manufacturer.objects.all(),
        label='Manufacturer (ID)',
    )
    manufacturer = ModelMultipleChoiceFilter(
        field_name='manufacturer__name',
        to_field_name='name',
        queryset=Manufacturer.objects.all(),
        label='Manufacturer (name)',
    )

    class Meta:
        model = ZabbixTemplateRule
        fields = ('id', 'name', 'description', 'pattern', 'role_pattern', 'require_tags', 'manufacturer', 'enabled', 'priority')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value) | Q(pattern__icontains=value) | Q(role_pattern__icontains=value) | Q(require_tags__icontains=value) | Q(manufacturer__name__icontains=value)).distinct()
