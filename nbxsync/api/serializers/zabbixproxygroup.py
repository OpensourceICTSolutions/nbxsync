from rest_framework import serializers
from netbox.api.serializers import NetBoxModelSerializer

from nbxsync.api.serializers import SyncInfoSerializerMixin, ZabbixServerSerializer
from nbxsync.models import ZabbixProxyGroup, ZabbixServer

__all__ = ('ZabbixProxyGroupSerializer',)


class ZabbixProxyGroupSerializer(SyncInfoSerializerMixin, NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixproxygroup-detail')

    zabbixserver = ZabbixServerSerializer(nested=True)
    zabbixserver_id = serializers.PrimaryKeyRelatedField(queryset=ZabbixServer.objects.all(), source='zabbixserver', write_only=True, required=False)

    class Meta:
        model = ZabbixProxyGroup
        fields = (
            'url',
            'id',
            'display',
            'name',
            'proxy_groupid',
            'description',
            'failover_delay',
            'min_online',
            'zabbixserver',
            'zabbixserver_id',
            'last_sync',
            'last_sync_state',
            'last_sync_message',
        )
        brief_fields = ('url', 'id', 'display', 'name')
