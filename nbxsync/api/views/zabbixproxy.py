from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixProxySerializer
from nbxsync.filtersets import ZabbixProxyFilterSet
from nbxsync.models import ZabbixProxy

__all__ = ('ZabbixProxyViewSet',)


class ZabbixProxyViewSet(NetBoxModelViewSet):
    queryset = ZabbixProxy.objects.all()
    serializer_class = ZabbixProxySerializer
    filterset_class = ZabbixProxyFilterSet
