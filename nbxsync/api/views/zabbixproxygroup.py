from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixProxyGroupSerializer
from nbxsync.filtersets import ZabbixProxyGroupFilterSet
from nbxsync.models import ZabbixProxyGroup

__all__ = ('ZabbixProxyGroupViewSet',)


class ZabbixProxyGroupViewSet(NetBoxModelViewSet):
    queryset = ZabbixProxyGroup.objects.all()
    serializer_class = ZabbixProxyGroupSerializer
    filterset_class = ZabbixProxyGroupFilterSet
