from rest_framework import serializers

from netbox.api.serializers import NetBoxModelSerializer

from nbxsync.api.serializers import SyncInfoSerializerMixin
from nbxsync.models import ZabbixServer

__all__ = ('ZabbixServerSerializer',)


class ZabbixServerSerializer(SyncInfoSerializerMixin, NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixserver-detail')

    class Meta:
        model = ZabbixServer
        fields = (
            'url',
            'id',
            'display',
            'name',
            'description',
            'url',
            'token',
            'validate_certs',
            'last_sync',
            'last_sync_state',
            'last_sync_message',
        )
        brief_fields = (
            'url',
            'id',
            'display',
            'name',
        )
