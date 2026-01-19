from rest_framework import serializers

from netbox.api.serializers import NetBoxModelSerializer

from nbxsync.models import ZabbixConfigurationGroup


__all__ = ('ZabbixConfigurationGroupSerializer',)


class ZabbixConfigurationGroupSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixconfigurationgroup-detail')

    class Meta:
        model = ZabbixConfigurationGroup
        fields = (
            'url',
            'id',
            'display',
            'name',
            'description',
        )
        brief_fields = ('url', 'id', 'display', 'name')
