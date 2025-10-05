from django import forms
from django.utils.translation import gettext as _

from netbox.forms import NetBoxModelImportForm, NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, TagFilterField, CSVModelChoiceField
from utilities.forms.rendering import FieldSet


from nbxsync.choices import HostInterfaceRequirementChoices
from nbxsync.models import ZabbixServer, ZabbixTemplate
from nbxsync.models.zabbixtemplate import default_interfacerequirement

__all__ = ('ZabbixTemplateForm', 'ZabbixTemplateFilterForm', 'ZabbixTemplateBulkImportForm', 'ZabbixTemplateBulkEditForm')


class ZabbixTemplateForm(NetBoxModelForm):
    name = forms.CharField(label=_('Name'), max_length=200, required=True)
    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=True, selector=True, label=_('Zabbix Server'))
    templateid = forms.IntegerField(label='Template ID')
    interface_requirements = forms.TypedMultipleChoiceField(choices=HostInterfaceRequirementChoices, required=False, coerce=int, initial=default_interfacerequirement, label=_('Required Host Interfaces'))

    class Meta:
        model = ZabbixTemplate
        fields = ('name', 'zabbixserver', 'templateid', 'interface_requirements')


class ZabbixTemplateFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixTemplate

    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=False, selector=True, label=_('Zabbix Server'))

    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet('name', 'zabbixserver', 'templateid', name=_('Zabbix Template')),
    )

    tag = TagFilterField(model)


class ZabbixTemplateBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixTemplate
    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=False, selector=True, label=_('Zabbix Server'))
    interface_requirements = forms.TypedMultipleChoiceField(choices=HostInterfaceRequirementChoices, required=False, coerce=int, initial=default_interfacerequirement, label=_('Required Host Interfaces'))

    fieldsets = (FieldSet('zabbixserver', 'interface_requirements'),)
    nullable_fields = ()

    def clean_interface_requirements(self):
        if not self.cleaned_data.get('interface_requirements'):
            return default_interfacerequirement()


class ZabbixTemplateBulkImportForm(NetBoxModelImportForm):
    zabbixserver = CSVModelChoiceField(queryset=ZabbixServer.objects.all(), to_field_name='name', help_text=_('Assigned Zabbix Server'))

    class Meta:
        model = ZabbixTemplate
        fields = (
            'zabbixserver',
            'templateid',
            'interface_requirements',
        )
