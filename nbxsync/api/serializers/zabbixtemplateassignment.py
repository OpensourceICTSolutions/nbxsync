from django.contrib.contenttypes.models import ContentType
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from utilities.api import get_serializer_for_model

from netbox.api.fields import ContentTypeField
from netbox.api.serializers import NetBoxModelSerializer

from nbxsync.api.serializers import ZabbixConfigurationGroupSerializer
from nbxsync.models import ZabbixTemplateAssignment, ZabbixConfigurationGroup


__all__ = ('ZabbixTemplateAssignmentSerializer',)


class ZabbixTemplateAssignmentSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixtemplateassignment-detail')
    assigned_object_type = ContentTypeField(queryset=ContentType.objects.all())
    assigned_object = serializers.SerializerMethodField(read_only=True)
    zabbixconfigurationgroup = ZabbixConfigurationGroupSerializer(nested=True, read_only=True, required=False)
    zabbixconfigurationgroup_id = serializers.PrimaryKeyRelatedField(queryset=ZabbixConfigurationGroup.objects.all(), source='zabbixconfigurationgroup', required=False)

    class Meta:
        model = ZabbixTemplateAssignment
        fields = (
            'url',
            'id',
            'display',
            'assigned_object_type',
            'assigned_object_id',
            'assigned_object',
            'zabbixconfigurationgroup',
            'zabbixconfigurationgroup_id',
            'zabbixtemplate',
        )

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_assigned_object(self, instance):
        serializer = get_serializer_for_model(instance.assigned_object_type.model_class())
        context = {'request': self.context['request']}
        return serializer(instance.assigned_object, context=context).data
