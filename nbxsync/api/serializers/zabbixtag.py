from rest_framework import serializers

from netbox.api.serializers import NetBoxModelSerializer

from nbxsync.models import ZabbixTag

__all__ = ('ZabbixTagSerializer',)


class ZabbixTagSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='plugins-api:nbxsync-api:zabbixtag-detail')

    class Meta:
        model = ZabbixTag
        fields = (
            'url',
            'id',
            'display',
            'name',
            'description',
            'tag',
            'value',
        )
        brief_fields = (
            'url',
            'id',
            'display',
            'name',
            'tag',
        )
