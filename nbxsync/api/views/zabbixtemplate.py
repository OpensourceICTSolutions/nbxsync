from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixTemplateSerializer
from nbxsync.filtersets import ZabbixTemplateFilterSet
from nbxsync.models import ZabbixTemplate

__all__ = ('ZabbixTemplateViewSet',)


class ZabbixTemplateViewSet(NetBoxModelViewSet):
    queryset = ZabbixTemplate.objects.all()
    serializer_class = ZabbixTemplateSerializer
    filterset_class = ZabbixTemplateFilterSet
