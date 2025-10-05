from django import forms
from django.utils.translation import gettext as _

from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import TagFilterField
from utilities.forms.rendering import FieldSet

from nbxsync.models import ZabbixTag


__all__ = (
    'ZabbixTagForm',
    'ZabbixTagFilterForm',
    'ZabbixTagBulkEditForm',
)


class ZabbixTagForm(NetBoxModelForm):
    name = forms.CharField(label=_('Name'), max_length=512, required=True)
    description = forms.CharField(label=_('Description'), max_length=512, required=False)
    tag = forms.CharField(label=_('Tag'), max_length=255, required=True)
    value = forms.CharField(label=_('Value'), max_length=512, required=False)

    class Meta:
        model = ZabbixTag
        fields = (
            'name',
            'description',
            'tag',
            'value',
        )


class ZabbixTagFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixTag
    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet('name', 'description', 'tag', 'value', name=_('Zabbix Tag')),
    )

    tag = TagFilterField(model)


class ZabbixTagBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixTag

    name = forms.CharField(label=_('Name'), max_length=512, required=False)
    description = forms.CharField(label=_('Description'), max_length=512, required=False)
    tag = forms.CharField(label=_('Tag'), max_length=512, required=False)
    value = forms.CharField(label=_('Value'), max_length=512, required=False)

    fieldsets = (FieldSet('name', 'description', 'tag', 'value', name=_('Zabbix Tag')),)
    nullable_fields = 'description'
