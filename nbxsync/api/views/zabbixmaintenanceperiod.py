from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixMaintenancePeriodSerializer
from nbxsync.filtersets import ZabbixMaintenancePeriodFilterSet
from nbxsync.models import ZabbixMaintenancePeriod

__all__ = ('ZabbixMaintenancePeriodViewSet',)


class ZabbixMaintenancePeriodViewSet(NetBoxModelViewSet):
    queryset = ZabbixMaintenancePeriod.objects.all()
    serializer_class = ZabbixMaintenancePeriodSerializer
    filterset_class = ZabbixMaintenancePeriodFilterSet
