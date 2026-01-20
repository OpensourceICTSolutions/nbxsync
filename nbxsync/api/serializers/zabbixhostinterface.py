from django.contrib.contenttypes.models import ContentType
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from utilities.api import get_serializer_for_model

from netbox.api.fields import ContentTypeField
from netbox.api.serializers import NetBoxModelSerializer

from nbxsync.api.serializers import SyncInfoSerializerMixin, ZabbixServerSerializer, ZabbixConfigurationGroupSerializer
from nbxsync.models import ZabbixHostInterface, ZabbixServer, ZabbixConfigurationGroup


class NestedZabbixHostInterfaceSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixhostinterface-detail')

    zabbixconfigurationgroup = ZabbixConfigurationGroupSerializer(nested=True, read_only=True, required=False)
    zabbixconfigurationgroup_id = serializers.PrimaryKeyRelatedField(queryset=ZabbixConfigurationGroup.objects.all(), source='zabbixconfigurationgroup', write_only=True, required=False)

    assigned_object_type = ContentTypeField(queryset=ContentType.objects.all())
    assigned_object = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ZabbixHostInterface
        fields = (
            'url',
            'id',
            'display',
            'zabbixserver',
            'zabbixserver_id',
            'zabbixconfigurationgroup',
            'zabbixconfigurationgroup_id',
            'type',
            'interfaceid',
            'dns',
            'port',
            'useip',
            'interface_type',
            'ip',
            'assigned_object_type',
            'assigned_object_id',
            'assigned_object',
            'tls_connect',
            'tls_accept',
            'tls_issuer',
            'tls_subject',
            'tls_psk_identity',
            'tls_psk',
            'snmp_version',
            'snmp_usebulk',
            'snmp_pushcommunity',
            'snmp_community',
            'snmpv3_context_name',
            'snmpv3_security_name',
            'snmpv3_security_level',
            'snmpv3_authentication_passphrase',
            'snmpv3_privacy_passphrase',
            'snmpv3_privacy_protocol',
            'ipmi_authtype',
            'ipmi_password',
            'ipmi_privilege',
            'ipmi_username',
            'last_sync',
            'last_sync_state',
            'last_sync_message',
        )
        brief_fields = (
            'url',
            'id',
            'display',
            'zabbixserver',
            'zabbixserver_id',
            'zabbixconfigurationgroup',
            'zabbixconfigurationgroup_id',
            'type',
            'interfaceid',
            'dns',
            'port',
            'useip',
            'interface_type',
            'ip',
            'assigned_object_type',
            'assigned_object_id',
            'assigned_object',
            'tls_connect',
            'tls_accept',
            'tls_issuer',
            'tls_subject',
            'tls_psk_identity',
            'tls_psk',
            'snmp_version',
            'snmp_usebulk',
            'snmp_pushcommunity',
            'snmp_community',
            'snmpv3_context_name',
            'snmpv3_security_name',
            'snmpv3_security_level',
            'snmpv3_authentication_passphrase',
            'snmpv3_privacy_passphrase',
            'snmpv3_privacy_protocol',
            'ipmi_authtype',
            'ipmi_password',
            'ipmi_privilege',
            'ipmi_username',
            'last_sync',
            'last_sync_state',
            'last_sync_message',
        )

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_assigned_object(self, instance):
        serializer = get_serializer_for_model(instance.assigned_object_type.model_class())
        context = {'request': self.context['request']}
        return serializer(instance.assigned_object, context=context).data


class ZabbixHostInterfaceSerializer(SyncInfoSerializerMixin, NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixhostinterface-detail')

    zabbixserver = ZabbixServerSerializer(nested=True)
    zabbixserver_id = serializers.PrimaryKeyRelatedField(queryset=ZabbixServer.objects.all(), source='zabbixserver', write_only=True, required=False)

    zabbixconfigurationgroup = ZabbixConfigurationGroupSerializer(nested=True, read_only=True, required=False)
    zabbixconfigurationgroup_id = serializers.PrimaryKeyRelatedField(queryset=ZabbixConfigurationGroup.objects.all(), source='zabbixconfigurationgroup', write_only=True, required=False)

    assigned_object_type = ContentTypeField(queryset=ContentType.objects.all())
    assigned_object = serializers.SerializerMethodField(read_only=True)

    parent = NestedZabbixHostInterfaceSerializer(nested=True, read_only=True, required=False)
    parent_id = serializers.PrimaryKeyRelatedField(queryset=ZabbixHostInterface.objects.all(), source='parent', required=False, allow_null=True)

    class Meta:
        model = ZabbixHostInterface
        fields = (
            'url',
            'id',
            'display',
            'zabbixserver',
            'zabbixserver_id',
            'zabbixconfigurationgroup',
            'zabbixconfigurationgroup_id',
            'type',
            'interfaceid',
            'dns',
            'port',
            'useip',
            'interface_type',
            'ip',
            'assigned_object_type',
            'assigned_object_id',
            'assigned_object',
            'tls_connect',
            'tls_accept',
            'tls_issuer',
            'tls_subject',
            'tls_psk_identity',
            'tls_psk',
            'snmp_version',
            'snmp_usebulk',
            'snmp_pushcommunity',
            'snmp_community',
            'snmpv3_context_name',
            'snmpv3_security_name',
            'snmpv3_security_level',
            'snmpv3_authentication_passphrase',
            'snmpv3_privacy_passphrase',
            'snmpv3_privacy_protocol',
            'ipmi_authtype',
            'ipmi_password',
            'ipmi_privilege',
            'ipmi_username',
            'parent',
            'parent_id',
            'last_sync',
            'last_sync_state',
            'last_sync_message',
        )

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_assigned_object(self, instance):
        serializer = get_serializer_for_model(instance.assigned_object_type.model_class())
        context = {'request': self.context['request']}
        return serializer(instance.assigned_object, context=context).data
