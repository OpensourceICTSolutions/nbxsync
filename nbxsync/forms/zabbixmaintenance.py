from django import forms
from django.utils.translation import gettext as _

from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField, TagFilterField
from utilities.forms.rendering import FieldSet
from utilities.forms.widgets import DateTimePicker

from nbxsync.choices import ZabbixMaintenanceTagsEvalChoices, ZabbixMaintenanceTypeChoices
from nbxsync.models import ZabbixMaintenance, ZabbixServer

__all__ = ('ZabbixMaintenanceForm', 'ZabbixMaintenanceFilterForm', 'ZabbixMaintenanceBulkEditForm')


class ZabbixMaintenanceForm(NetBoxModelForm):
    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=True, selector=True, label=_('Zabbix Server'))
    name = forms.CharField(label=_('Name'), max_length=512, required=True)
    description = forms.CharField(label=_('Description'), required=False, widget=forms.Textarea(attrs={'rows': 1, 'cols': 40}))
    active_since = forms.DateTimeField(label=_('Active since'), widget=DateTimePicker(), required=True)
    active_till = forms.DateTimeField(label=_('Active till'), widget=DateTimePicker(), required=True)
    maintenance_type = forms.ChoiceField(label=_('Maintenance type'), choices=ZabbixMaintenanceTypeChoices.choices, required=True)
    tags_evaltype = forms.ChoiceField(label=_('Tags evaluation type'), choices=ZabbixMaintenanceTagsEvalChoices.choices, required=True)

    fieldsets = (
        FieldSet('name', 'description', name=_('General')),
        FieldSet('maintenanceid', 'maintenance_type', 'tags_evaltype', name=_('Zabbix')),
        FieldSet('active_since', 'active_till', name=_('Window')),
        FieldSet('zabbixserver', name=_('Assignment')),
    )

    class Meta:
        model = ZabbixMaintenance
        fields = (
            'zabbixserver',
            'name',
            'active_since',
            'active_till',
            'description',
            'maintenance_type',
            'tags_evaltype',
        )

    def clean(self):
        super().clean()

        since = self.cleaned_data.get('active_since')
        till = self.cleaned_data.get('active_till')
        if since and till and till <= since:
            raise forms.ValidationError({'active_till': _('“Active till” must be later than “Active since”.')})


class ZabbixMaintenanceFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixMaintenance

    zabbixserver = DynamicModelMultipleChoiceField(queryset=ZabbixServer.objects.all(), required=False, label=_('Zabbix Server (name)'), to_field_name='name')
    zabbixserver_id = DynamicModelMultipleChoiceField(queryset=ZabbixServer.objects.all(), required=False, label=_('Zabbix Server (ID)'))
    maintenance_type = forms.MultipleChoiceField(choices=ZabbixMaintenanceTypeChoices.choices, required=False, label=_('Maintenance type'))
    tags_evaltype = forms.MultipleChoiceField(choices=ZabbixMaintenanceTagsEvalChoices.choices, required=False, label=_('Tags evaluation type'))
    name = forms.CharField(required=False, label=_('Name'))
    description = forms.CharField(label=_('Description'), required=False, widget=forms.Textarea(attrs={'rows': 1, 'cols': 40}))

    active_since_after = forms.DateTimeField(required=False, label=_('Active since after'), widget=DateTimePicker())
    active_since_before = forms.DateTimeField(required=False, label=_('Active since before'), widget=DateTimePicker())
    active_till_after = forms.DateTimeField(required=False, label=_('Active till after'), widget=DateTimePicker())
    active_till_before = forms.DateTimeField(required=False, label=_('Active till before'), widget=DateTimePicker())

    fieldsets = (
        FieldSet('q', 'filter_id', name=_('Search')),
        FieldSet('name', 'description', name=_('Attributes')),
        FieldSet('maintenance_type', 'tags_evaltype', name=_('Zabbix')),
        FieldSet('active_since_after', 'active_since_before', 'active_till_after', 'active_till_before', name=_('Window')),
        FieldSet('zabbixserver', 'zabbixserver_id', name=_('Assignment')),
    )

    tag = TagFilterField(model)


class ZabbixMaintenanceBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixMaintenance

    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=False, selector=True, label=_('Zabbix Server'))
    name = forms.CharField(label=_('Name'), max_length=512, required=False)
    description = forms.CharField(label=_('Description'), required=False, widget=forms.Textarea(attrs={'rows': 1, 'cols': 40}))
    active_since = forms.DateTimeField(label=_('Active since'), widget=DateTimePicker(), required=False)
    active_till = forms.DateTimeField(label=_('Active till'), widget=DateTimePicker(), required=False)
    maintenance_type = forms.ChoiceField(choices=ZabbixMaintenanceTypeChoices.choices, required=False, label=_('Maintenance type'))
    tags_evaltype = forms.ChoiceField(choices=ZabbixMaintenanceTagsEvalChoices.choices, required=False, label=_('Tags evaluation type'))

    fieldsets = (
        FieldSet(
            'zabbixserver',
            'name',
            'description',
            'maintenance_type',
            'tags_evaltype',
            'active_since',
            'active_till',
        ),
    )

    nullable_fields = ('description',)
