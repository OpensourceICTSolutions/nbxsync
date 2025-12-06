from rest_framework import serializers
from netbox.api.serializers import NetBoxModelSerializer

from nbxsync.api.serializers import SyncInfoSerializerMixin, ZabbixProxyGroupSerializer, ZabbixServerSerializer
from nbxsync.models import ZabbixProxy, ZabbixProxyGroup, ZabbixServer

__all__ = ('ZabbixProxySerializer',)


class ZabbixProxySerializer(SyncInfoSerializerMixin, NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixproxy-detail')

    zabbixserver = ZabbixServerSerializer(nested=True)
    zabbixserver_id = serializers.PrimaryKeyRelatedField(queryset=ZabbixServer.objects.all(), source='zabbixserver', write_only=True, required=False)

    proxygroup = ZabbixProxyGroupSerializer(nested=True, required=False)
    proxygroup_id = serializers.PrimaryKeyRelatedField(queryset=ZabbixProxyGroup.objects.all(), source='proxygroup', write_only=True, required=False)

    class Meta:
        model = ZabbixProxy
        fields = (
            'url',
            'id',
            'display',
            'name',
            'proxyid',
            'zabbixserver',
            'zabbixserver_id',
            'proxygroup',
            'proxygroup_id',
            'local_address',
            'local_port',
            'operating_mode',
            'description',
            'address',
            'port',
            'allowed_addresses',
            'tls_connect',
            'tls_accept',
            'tls_issuer',
            'tls_subject',
            'tls_psk_identity',
            'tls_psk',
            'custom_timeouts',
            'timeout_zabbix_agent',
            'timeout_simple_check',
            'timeout_snmp_agent',
            'timeout_external_check',
            'timeout_db_monitor',
            'timeout_http_agent',
            'timeout_ssh_agent',
            'timeout_telnet_agent',
            'timeout_script',
            'timeout_browser',
            'last_sync',
            'last_sync_state',
            'last_sync_message',
        )
        brief_fields = ('url', 'id', 'display', 'name')
