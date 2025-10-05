from rest_framework import serializers
from netbox.api.serializers import NetBoxModelSerializer

from nbxsync.models import ZabbixMaintenanceTagAssignment

__all__ = ('ZabbixMaintenanceTagAssignmentSerializer',)


class ZabbixMaintenanceTagAssignmentSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixmaintenancetagassignment-detail')

    class Meta:
        model = ZabbixMaintenanceTagAssignment
        fields = (
            'url',
            'id',
            'display',
            'zabbixmaintenance',
            'zabbixtag',
            'operator',
            'value',
            'created',
            'last_updated',
        )
        brief_fields = ('url', 'id', 'display')
