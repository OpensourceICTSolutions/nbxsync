from django.contrib.contenttypes.models import ContentType
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from utilities.api import get_serializer_for_model

from netbox.api.fields import ContentTypeField
from netbox.api.serializers import NetBoxModelSerializer

from nbxsync.models import ZabbixConfigurationGroupAssignment

__all__ = ('ZabbixConfigurationGroupAssignmentSerializer',)


class ZabbixConfigurationGroupAssignmentSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixconfigurationgroupassignment-detail')
    assigned_object_type = ContentTypeField(queryset=ContentType.objects.all())
    assigned_object = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ZabbixConfigurationGroupAssignment
        fields = (
            'url',
            'id',
            'display',
            'assigned_object_type',
            'assigned_object_id',
            'assigned_object',
            'zabbixconfigurationgroup',
        )

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_assigned_object(self, instance):
        if instance.assigned_object_type is None or instance.assigned_object is None:
            return None
        model = instance.assigned_object_type.model_class()
        if model is None:
            return None
        serializer = get_serializer_for_model(model)
        context = {'request': self.context['request']}
        return serializer(instance.assigned_object, context=context).data
