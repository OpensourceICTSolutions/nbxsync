from netbox.views.generic import BulkDeleteView, BulkEditView, ObjectDeleteView, ObjectEditView, ObjectListView, ObjectView

from utilities.views import register_model_view

from nbxsync.filtersets import ZabbixTemplateRuleFilterSet
from nbxsync.forms import ZabbixTemplateRuleBulkEditForm, ZabbixTemplateRuleFilterForm, ZabbixTemplateRuleForm
from nbxsync.models import ZabbixTemplateRule
from nbxsync.tables import ZabbixTemplateRuleTable

__all__ = (
    'ZabbixTemplateRuleListView',
    'ZabbixTemplateRuleView',
    'ZabbixTemplateRuleEditView',
    'ZabbixTemplateRuleBulkEditView',
    'ZabbixTemplateRuleDeleteView',
    'ZabbixTemplateRuleBulkDeleteView',
)


@register_model_view(ZabbixTemplateRule, name='list')
class ZabbixTemplateRuleListView(ObjectListView):
    queryset = ZabbixTemplateRule.objects.select_related('zabbixtemplate', 'zabbixhostgroup', 'zabbixtag', 'manufacturer')
    table = ZabbixTemplateRuleTable
    filterset = ZabbixTemplateRuleFilterSet
    filterset_form = ZabbixTemplateRuleFilterForm


@register_model_view(ZabbixTemplateRule)
class ZabbixTemplateRuleView(ObjectView):
    queryset = ZabbixTemplateRule.objects.select_related('zabbixtemplate', 'zabbixhostgroup', 'zabbixtag', 'manufacturer')


@register_model_view(ZabbixTemplateRule, 'edit')
class ZabbixTemplateRuleEditView(ObjectEditView):
    queryset = ZabbixTemplateRule.objects.select_related('zabbixtemplate', 'zabbixhostgroup', 'zabbixtag', 'manufacturer')
    form = ZabbixTemplateRuleForm


@register_model_view(ZabbixTemplateRule, 'bulk_edit')
class ZabbixTemplateRuleBulkEditView(BulkEditView):
    queryset = ZabbixTemplateRule.objects.select_related('zabbixtemplate', 'zabbixhostgroup', 'zabbixtag', 'manufacturer')
    filterset = ZabbixTemplateRuleFilterSet
    table = ZabbixTemplateRuleTable
    form = ZabbixTemplateRuleBulkEditForm


@register_model_view(ZabbixTemplateRule, 'delete')
class ZabbixTemplateRuleDeleteView(ObjectDeleteView):
    queryset = ZabbixTemplateRule.objects.all()


@register_model_view(ZabbixTemplateRule, 'bulk_delete')
class ZabbixTemplateRuleBulkDeleteView(BulkDeleteView):
    queryset = ZabbixTemplateRule.objects.all()
    filterset = ZabbixTemplateRuleFilterSet
    table = ZabbixTemplateRuleTable
