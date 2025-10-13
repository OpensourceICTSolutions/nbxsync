from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django_filters import CharFilter, ModelChoiceFilter, NumberFilter

from utilities.filters import ContentTypeFilter
from netbox.filtersets import NetBoxModelFilterSet

from nbxsync.models import ZabbixHostInventory


__all__ = ('ZabbixHostInventoryFilterSet',)


class ZabbixHostInventoryFilterSet(NetBoxModelFilterSet):
    q = CharFilter(method='search', label='Search')

    alias = CharFilter(lookup_expr='icontains')
    tag = CharFilter(lookup_expr='icontains')
    vendor = CharFilter(lookup_expr='icontains')
    location = CharFilter(lookup_expr='icontains')

    assigned_object_type = ContentTypeFilter()
    assigned_object_id = NumberFilter()

    class Meta:
        model = ZabbixHostInventory
        fields = (
            'inventory_mode',
            'alias',
            'asset_tag',
            'chassis',
            'contact',
            'contract_number',
            'date_hw_decomm',
            'date_hw_expiry',
            'date_hw_install',
            'date_hw_purchase',
            'deployment_status',
            'hardware',
            'hardware_full',
            'host_netmask',
            'host_networks',
            'host_router',
            'hw_arch',
            'installer_name',
            'location',
            'location_lat',
            'location_lon',
            'macaddress_a',
            'macaddress_b',
            'model_field',
            'name',
            'notes',
            'oob_ip',
            'oob_netmask',
            'oob_router',
            'os',
            'os_full',
            'os_short',
            'poc_1_cell',
            'poc_1_email',
            'poc_1_name',
            'poc_1_notes',
            'poc_1_phone_a',
            'poc_1_phone_b',
            'poc_1_screen',
            'poc_2_cell',
            'poc_2_email',
            'poc_2_name',
            'poc_2_notes',
            'poc_2_phone_a',
            'poc_2_phone_b',
            'poc_2_screen',
            'serialno_a',
            'serialno_b',
            'site_address_a',
            'site_address_b',
            'site_address_c',
            'site_city',
            'site_country',
            'site_notes',
            'site_rack',
            'site_state',
            'site_zip',
            'software',
            'software_app_a',
            'software_app_b',
            'software_app_c',
            'software_app_d',
            'software_app_e',
            'software_full',
            'tag',
            'type',
            'type_full',
            'url_a',
            'url_b',
            'url_c',
            'vendor',
            'assigned_object_type',
            'assigned_object_id',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset

        search_fields = [
            'alias',
            'asset_tag',
            'chassis',
            'contact',
            'contract_number',
            'date_hw_decomm',
            'date_hw_expiry',
            'date_hw_install',
            'date_hw_purchase',
            'deployment_status',
            'hardware',
            'hardware_full',
            'host_netmask',
            'host_networks',
            'host_router',
            'hw_arch',
            'installer_name',
            'location',
            'location_lat',
            'location_lon',
            'macaddress_a',
            'macaddress_b',
            'model_field',
            'name',
            'notes',
            'oob_ip',
            'oob_netmask',
            'oob_router',
            'os',
            'os_full',
            'os_short',
            'poc_1_cell',
            'poc_1_email',
            'poc_1_name',
            'poc_1_notes',
            'poc_1_phone_a',
            'poc_1_phone_b',
            'poc_1_screen',
            'poc_2_cell',
            'poc_2_email',
            'poc_2_name',
            'poc_2_notes',
            'poc_2_phone_a',
            'poc_2_phone_b',
            'poc_2_screen',
            'serialno_a',
            'serialno_b',
            'site_address_a',
            'site_address_b',
            'site_address_c',
            'site_city',
            'site_country',
            'site_notes',
            'site_rack',
            'site_state',
            'site_zip',
            'software',
            'software_app_a',
            'software_app_b',
            'software_app_c',
            'software_app_d',
            'software_app_e',
            'software_full',
            'tag',
            'type',
            'type_full',
            'url_a',
            'url_b',
            'url_c',
            'vendor',
        ]

        query = Q()
        for field in search_fields:
            query |= Q(**{f'{field}__icontains': value})

        return queryset.filter(query).distinct()
