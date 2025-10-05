from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixTagSerializer
from nbxsync.filtersets import ZabbixTagFilterSet
from nbxsync.models import ZabbixTag

__all__ = ('ZabbixTagViewSet',)


class ZabbixTagViewSet(NetBoxModelViewSet):
    queryset = ZabbixTag.objects.all()
    serializer_class = ZabbixTagSerializer
    filterset_class = ZabbixTagFilterSet
