from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixMaintenanceSerializer
from nbxsync.filtersets import ZabbixMaintenanceFilterSet
from nbxsync.models import ZabbixMaintenance

__all__ = ('ZabbixMaintenanceViewSet',)


class ZabbixMaintenanceViewSet(NetBoxModelViewSet):
    queryset = ZabbixMaintenance.objects.all()
    serializer_class = ZabbixMaintenanceSerializer
    filterset_class = ZabbixMaintenanceFilterSet
