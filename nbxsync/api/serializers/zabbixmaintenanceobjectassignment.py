from django.contrib.contenttypes.models import ContentType
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from utilities.api import get_serializer_for_model

from netbox.api.fields import ContentTypeField
from netbox.api.serializers import NetBoxModelSerializer

from nbxsync.models import ZabbixMaintenanceObjectAssignment

__all__ = ('ZabbixMaintenanceObjectAssignmentSerializer',)


class ZabbixMaintenanceObjectAssignmentSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixmaintenanceobjectassignment-detail')
    assigned_object_type = ContentTypeField(queryset=ContentType.objects.all())
    assigned_object = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ZabbixMaintenanceObjectAssignment
        fields = (
            'url',
            'id',
            'display',
            'zabbixmaintenance',
            'assigned_object_type',
            'assigned_object_id',
            'assigned_object',
            'created',
            'last_updated',
        )
        brief_fields = ('url', 'id', 'display')

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_assigned_object(self, instance):
        serializer = get_serializer_for_model(instance.assigned_object_type.model_class())
        context = {'request': self.context['request']}
        return serializer(instance.assigned_object, context=context).data
