from django import forms
from django.utils.translation import gettext as _

from netbox.forms import NetBoxModelImportForm, NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import TagFilterField
from utilities.forms.rendering import FieldSet


from nbxsync.models import ZabbixConfigurationGroup

__all__ = ('ZabbixConfigurationGroupForm', 'ZabbixConfigurationGroupFilterForm', 'ZabbixConfigurationGroupBulkImportForm', 'ZabbixConfigurationGroupBulkEditForm')


class ZabbixConfigurationGroupForm(NetBoxModelForm):
    name = forms.CharField(label=_('Name'), max_length=200, required=True)
    description = forms.CharField(label=_('Description'), max_length=200, required=False)

    fieldsets = (FieldSet('name', 'description', name=_('Generic')),)

    class Meta:
        model = ZabbixConfigurationGroup
        fields = (
            'name',
            'description',
        )


class ZabbixConfigurationGroupFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixConfigurationGroup

    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet('name', 'description', name=_('Zabbix Configuration Group')),
    )

    tag = TagFilterField(model)


class ZabbixConfigurationGroupBulkImportForm(NetBoxModelImportForm):
    class Meta:
        model = ZabbixConfigurationGroup
        fields = (
            'name',
            'description',
        )


class ZabbixConfigurationGroupBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixConfigurationGroup
    name = forms.CharField(label=_('Name'), max_length=200, required=False)
    description = forms.CharField(label=_('Description'), max_length=1024, required=False)

    fieldsets = (
        FieldSet(
            'name',
            'description',
        ),
    )
    nullable_fields = ()
