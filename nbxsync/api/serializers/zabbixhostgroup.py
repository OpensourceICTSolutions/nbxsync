from nbxsync.api.serializers import ZabbixServerSerializer
from nbxsync.models import ZabbixHostgroup, ZabbixServer
from netbox.api.serializers import NetBoxModelSerializer
from rest_framework import serializers

__all__ = ('ZabbixHostgroupSerializer',)


class ZabbixHostgroupSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixhostgroup-detail')
    zabbixserver = ZabbixServerSerializer(read_only=True, nested=True)
    zabbixserver_id = serializers.PrimaryKeyRelatedField(queryset=ZabbixServer.objects.all(), source='zabbixserver', write_only=True, required=False)

    class Meta:
        model = ZabbixHostgroup
        fields = (
            'url',
            'id',
            'display',
            'name',
            'description',
            'value',
            'groupid',
            'zabbixserver',
            'zabbixserver_id',
        )
        brief_fields = ('url', 'id', 'display', 'name')
