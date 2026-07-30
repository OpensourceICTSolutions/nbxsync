from rest_framework import serializers

from netbox.api.serializers import NetBoxModelSerializer

from nbxsync.api.serializers.zabbixhostgroup import ZabbixHostgroupSerializer
from nbxsync.api.serializers.zabbixtag import ZabbixTagSerializer
from nbxsync.api.serializers.zabbixtemplate import ZabbixTemplateSerializer
from nbxsync.models import ZabbixTemplateRule

__all__ = ('ZabbixTemplateRuleSerializer',)


class ZabbixTemplateRuleSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixtemplaterule-detail')
    zabbixtemplate = ZabbixTemplateSerializer(nested=True)
    zabbixhostgroup = ZabbixHostgroupSerializer(nested=True, required=False, allow_null=True)
    zabbixtag = ZabbixTagSerializer(nested=True, required=False, allow_null=True)

    class Meta:
        model = ZabbixTemplateRule
        fields = (
            'url',
            'id',
            'display',
            'name',
            'description',
            'pattern',
            'zabbixtemplate',
            'zabbixhostgroup',
            'zabbixtag',
            'enabled',
            'priority',
            'tags',
            'custom_fields',
            'created',
            'last_updated',
        )
        brief_fields = (
            'url',
            'id',
            'display',
            'name',
            'pattern',
            'enabled',
        )
