from django.contrib.contenttypes.models import ContentType
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from utilities.api import get_serializer_for_model

from netbox.api.fields import ContentTypeField
from netbox.api.serializers import NetBoxModelSerializer

from nbxsync.api.serializers import SyncInfoSerializerMixin, ZabbixConfigurationGroupSerializer
from nbxsync.models import ZabbixMacroAssignment, ZabbixConfigurationGroup

__all__ = ('ZabbixMacroAssignmentSerializer', 'NestedZabbixMacroAssignmentSerializer')


class NestedZabbixMacroAssignmentSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixmacroassignment-detail')

    class Meta:
        model = ZabbixMacroAssignment
        fields = (
            'id',
            'url',
            'display',
            'zabbixmacro',
            'is_regex',
            'context',
            'value',
        )
        brief_fields = ('id', 'display', 'zabbixmacro', 'is_regex', 'context', 'value')


class ZabbixMacroAssignmentSerializer(SyncInfoSerializerMixin, NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixmacroassignment-detail')
    assigned_object_type = ContentTypeField(queryset=ContentType.objects.all())
    assigned_object = serializers.SerializerMethodField(read_only=True)

    zabbixconfigurationgroup = ZabbixConfigurationGroupSerializer(nested=True, read_only=True, required=False)
    zabbixconfigurationgroup_id = serializers.PrimaryKeyRelatedField(queryset=ZabbixConfigurationGroup.objects.all(), source='zabbixconfigurationgroup', required=False)

    parent = NestedZabbixMacroAssignmentSerializer(nested=True, read_only=True, required=False)
    parent_id = serializers.PrimaryKeyRelatedField(queryset=ZabbixMacroAssignment.objects.all(), source='parent', required=False, allow_null=True)

    class Meta:
        model = ZabbixMacroAssignment
        fields = (
            'url',
            'id',
            'display',
            'assigned_object_type',
            'assigned_object_id',
            'assigned_object',
            'zabbixconfigurationgroup',
            'zabbixconfigurationgroup_id',
            'zabbixmacro',
            'macroid',
            'is_regex',
            'context',
            'value',
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
