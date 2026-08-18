from netbox.api.viewsets import NetBoxModelViewSet

from nbxsync.api.serializers import ZabbixTemplateRuleSerializer
from nbxsync.filtersets import ZabbixTemplateRuleFilterSet
from nbxsync.models import ZabbixTemplateRule

__all__ = ('ZabbixTemplateRuleViewSet',)


class ZabbixTemplateRuleViewSet(NetBoxModelViewSet):
    queryset = ZabbixTemplateRule.objects.all().select_related('zabbixtemplate', 'zabbixhostgroup', 'zabbixtag', 'manufacturer')
    serializer_class = ZabbixTemplateRuleSerializer
    filterset_class = ZabbixTemplateRuleFilterSet
