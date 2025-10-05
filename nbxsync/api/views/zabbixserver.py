from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixServerSerializer
from nbxsync.filtersets import ZabbixServerFilterSet
from nbxsync.models import ZabbixServer

__all__ = ('ZabbixServerViewSet',)


class ZabbixServerViewSet(NetBoxModelViewSet):
    queryset = ZabbixServer.objects.all()
    serializer_class = ZabbixServerSerializer
    filterset_class = ZabbixServerFilterSet
