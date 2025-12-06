from rest_framework import serializers

from netbox.api.serializers import NetBoxModelSerializer

from nbxsync.api.serializers import ZabbixServerSerializer
from nbxsync.choices import HostInterfaceRequirementChoices
from nbxsync.models import ZabbixServer, ZabbixTemplate

__all__ = ('ZabbixTemplateSerializer',)


class ZabbixTemplateSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixtemplate-detail')
    zabbixserver = ZabbixServerSerializer(nested=True)
    zabbixserver_id = serializers.PrimaryKeyRelatedField(queryset=ZabbixServer.objects.all(), source='zabbixserver', write_only=True, required=False)
    interface_requirements = serializers.ListField(child=serializers.ChoiceField(choices=HostInterfaceRequirementChoices.choices), required=False, allow_empty=True)

    class Meta:
        model = ZabbixTemplate
        fields = (
            'url',
            'id',
            'display',
            'name',
            'templateid',
            'zabbixserver',
            'zabbixserver_id',
            'interface_requirements',
        )
        brief_fields = ('url', 'id', 'display', 'name')
