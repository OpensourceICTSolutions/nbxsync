from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixMacroSerializer
from nbxsync.filtersets import ZabbixMacroFilterSet
from nbxsync.models import ZabbixMacro

__all__ = ('ZabbixMacroViewSet',)


class ZabbixMacroViewSet(NetBoxModelViewSet):
    queryset = ZabbixMacro.objects.all()
    serializer_class = ZabbixMacroSerializer
    filterset_class = ZabbixMacroFilterSet
