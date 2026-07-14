from django import forms
from django.utils.translation import gettext as _

from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField
from utilities.forms.rendering import FieldSet

from nbxsync.models import ZabbixHostgroup, ZabbixTag, ZabbixTemplate, ZabbixTemplateRule

__all__ = (
    'ZabbixTemplateRuleForm',
    'ZabbixTemplateRuleFilterForm',
    'ZabbixTemplateRuleBulkEditForm',
)


class ZabbixTemplateRuleForm(NetBoxModelForm):
    zabbixtemplate = DynamicModelChoiceField(queryset=ZabbixTemplate.objects.all(), selector=True, label=_('Zabbix Template'))
    zabbixhostgroup = DynamicModelChoiceField(queryset=ZabbixHostgroup.objects.all(), required=False, selector=True, label=_('Zabbix Hostgroup'))
    zabbixtag = DynamicModelChoiceField(queryset=ZabbixTag.objects.all(), required=False, selector=True, label=_('Zabbix Tag'))

    class Meta:
        model = ZabbixTemplateRule
        fields = (
            'name',
            'description',
            'pattern',
            'zabbixtemplate',
            'zabbixhostgroup',
            'zabbixtag',
            'enabled',
            'priority',
        )


class ZabbixTemplateRuleFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixTemplateRule
    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet('name', 'description', 'pattern', 'enabled', name=_('Zabbix Template Rule')),
    )

    enabled = forms.NullBooleanField(required=False, label=_('Enabled'))


class ZabbixTemplateRuleBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixTemplateRule

    description = forms.CharField(label=_('Description'), max_length=200, required=False)
    pattern = forms.CharField(label=_('Pattern'), max_length=500, required=False)
    zabbixtemplate = forms.ModelChoiceField(queryset=ZabbixTemplate.objects.all(), required=False, label=_('Zabbix Template'))
    zabbixhostgroup = forms.ModelChoiceField(queryset=ZabbixHostgroup.objects.all(), required=False, label=_('Zabbix Hostgroup'))
    zabbixtag = forms.ModelChoiceField(queryset=ZabbixTag.objects.all(), required=False, label=_('Zabbix Tag'))
    enabled = forms.NullBooleanField(required=False, label=_('Enabled'))
    priority = forms.IntegerField(required=False, label=_('Priority'))

    fieldsets = (FieldSet('description', 'pattern', 'zabbixtemplate', 'zabbixhostgroup', 'zabbixtag', 'enabled', 'priority', name=_('Zabbix Template Rule')),)
    nullable_fields = ('description', 'zabbixhostgroup', 'zabbixtag')
