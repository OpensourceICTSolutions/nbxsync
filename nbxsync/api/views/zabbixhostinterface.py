from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixHostInterfaceSerializer
from nbxsync.filtersets import ZabbixHostInterfaceFilterSet
from nbxsync.models import ZabbixHostInterface

__all__ = ('ZabbixHostInterfaceViewSet',)


class ZabbixHostInterfaceViewSet(NetBoxModelViewSet):
    queryset = ZabbixHostInterface.objects.all()
    serializer_class = ZabbixHostInterfaceSerializer
    filterset_class = ZabbixHostInterfaceFilterSet
