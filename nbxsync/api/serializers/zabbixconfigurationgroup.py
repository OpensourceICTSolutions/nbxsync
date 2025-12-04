from nbxsync.api.serializers import ZabbixServerSerializer
from nbxsync.models import ZabbixHostgroup, ZabbixServer
from netbox.api.serializers import NetBoxModelSerializer
from rest_framework import serializers

__all__ = ('ZabbixConfigurationGroupSerializer',)


class ZabbixConfigurationGroupSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixconfigurationgroup-detail')

    class Meta:
        model = ZabbixHostgroup
        fields = (
            'url',
            'id',
            'display',
            'name',
            'description',
        )
        brief_fields = ('url', 'id', 'display', 'name')
