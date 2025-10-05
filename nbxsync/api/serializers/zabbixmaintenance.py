from rest_framework import serializers
from netbox.api.fields import ChoiceField
from netbox.api.serializers import NetBoxModelSerializer

from nbxsync.api.serializers import SyncInfoSerializerMixin
from nbxsync.models import ZabbixMaintenance

__all__ = ('ZabbixMaintenanceSerializer',)


class ZabbixMaintenanceSerializer(SyncInfoSerializerMixin, NetBoxModelSerializer):
    """
    Serializer for ZabbixMaintenance with nested FK and choice fields.
    """

    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixmaintenance-detail')
    automatic = serializers.BooleanField(read_only=True)

    # Choice fields return the value; *_display returns the human label
    maintenance_type = ChoiceField(choices=ZabbixMaintenance._meta.get_field('maintenance_type').choices)
    maintenance_type_display = serializers.CharField(source='get_maintenance_type_display', read_only=True)

    tags_evaltype = ChoiceField(choices=ZabbixMaintenance._meta.get_field('tags_evaltype').choices)
    tags_evaltype_display = serializers.CharField(source='get_tags_evaltype_display', read_only=True)

    class Meta:
        model = ZabbixMaintenance
        fields = (
            'url',
            'id',
            'display',
            'name',
            'description',
            'maintenanceid',
            'active_since',
            'active_till',
            'maintenance_type',
            'maintenance_type_display',
            'tags_evaltype',
            'tags_evaltype_display',
            'zabbixserver',
            'zabbixserver_id',
            'last_sync',
            'last_sync_state',
            'last_sync_message',
            'automatic',
            'created',
            'last_updated',
        )
        brief_fields = ('url', 'id', 'display', 'name')
