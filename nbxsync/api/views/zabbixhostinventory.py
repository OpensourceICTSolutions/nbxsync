from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixHostInventorySerializer
from nbxsync.filtersets import ZabbixHostInventoryFilterSet
from nbxsync.models import ZabbixHostInventory

__all__ = ('ZabbixHostInventoryViewSet',)


class ZabbixHostInventoryViewSet(NetBoxModelViewSet):
    queryset = ZabbixHostInventory.objects.all()
    serializer_class = ZabbixHostInventorySerializer
    filterset_class = ZabbixHostInventoryFilterSet
