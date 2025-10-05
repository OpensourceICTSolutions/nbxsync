from django.contrib.contenttypes.models import ContentType
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from utilities.api import get_serializer_for_model

from netbox.api.fields import ContentTypeField
from netbox.api.serializers import NetBoxModelSerializer

from nbxsync.models import ZabbixHostInventory

__all__ = ('ZabbixHostInventorySerializer',)


class ZabbixHostInventorySerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixhostinventory-detail')
    assigned_object_type = ContentTypeField(queryset=ContentType.objects.all())
    assigned_object = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ZabbixHostInventory
        fields = (
            'url',
            'id',
            'display',
            # Inventory fields
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
            'assigned_object',
        )
        brief_fields = ('id', 'display', 'alias', 'name')

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_assigned_object(self, instance):
        serializer_class = get_serializer_for_model(instance.assigned_object_type.model_class())
        context = {'request': self.context.get('request')}
        return serializer_class(instance.assigned_object, context=context).data
