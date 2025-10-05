from django.contrib.contenttypes.models import ContentType
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from utilities.api import get_serializer_for_model

from netbox.api.fields import ContentTypeField
from netbox.api.serializers import NetBoxModelSerializer

from nbxsync.api.serializers import SyncInfoSerializerMixin, ZabbixServerSerializer
from nbxsync.models import ZabbixHostInterface, ZabbixServer


class ZabbixHostInterfaceSerializer(SyncInfoSerializerMixin, NetBoxModelSerializer):
    zabbixserver = ZabbixServerSerializer(nested=True)
    zabbixserver_id = serializers.PrimaryKeyRelatedField(queryset=ZabbixServer.objects.all(), source='zabbixserver', write_only=True)

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

    @extend_schema_field(OpenApiTypes.STR)
    def get_assigned_object(self, instance):
        serializer = get_serializer_for_model(instance.assigned_object_type.model_class())
        context = {'request': self.context['request']}
        return serializer(instance.assigned_object, context=context).data
