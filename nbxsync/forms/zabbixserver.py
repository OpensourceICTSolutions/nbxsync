from django import forms
from django.utils.translation import gettext as _

from netbox.forms import NetBoxModelImportForm, NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import TagFilterField
from utilities.forms.rendering import FieldSet

from nbxsync.models import ZabbixServer

__all__ = ('ZabbixServerForm', 'ZabbixServerFilterForm', 'ZabbixServerBulkImportForm', 'ZabbixServerBulkEditForm')


BOOLEAN_WITH_BLANK_CHOICES = (
    ('', '---------'),
    (True, 'Yes'),
    (False, 'No'),
)


class ZabbixServerForm(NetBoxModelForm):
    name = forms.CharField(label=_('Name'), max_length=200, required=True)
    description = forms.CharField(label=_('Description'), required=False, widget=forms.Textarea(attrs={'rows': 1, 'cols': 40}))
    url = forms.URLField(label=_('URL'), max_length=200, required=True)
    token = forms.CharField(label=_('Token'), max_length=200, required=True, widget=forms.PasswordInput(render_value=True))

    validate_certs = forms.BooleanField(label=_('Validate HTTPS Certificate'), required=False)

    class Meta:
        model = ZabbixServer
        fields = (
            'name',
            'description',
            'url',
            'validate_certs',
            'token',
        )


class ZabbixServerFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixServer
    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet('name', 'description', 'validate_certs', 'url', name=_('Zabbix Server')),
    )

    tag = TagFilterField(model)


class ZabbixServerBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixServer

    name = forms.CharField(label=_('Name'), max_length=200, required=False)
    description = forms.CharField(label=_('Description'), required=False, widget=forms.Textarea(attrs={'rows': 1, 'cols': 40}))
    url = forms.CharField(label=_('URL'), max_length=200, required=False)
    token = forms.CharField(label=_('Token'), max_length=200, required=False)
    validate_certs = forms.TypedChoiceField(label=_('Validate HTTPS Certificate'), choices=BOOLEAN_WITH_BLANK_CHOICES, coerce=lambda x: x == 'True', required=False)

    fieldsets = (FieldSet('name', 'description', 'url', 'token', 'validate_certs'),)
    nullable_fields = ()


class ZabbixServerBulkImportForm(NetBoxModelImportForm):
    class Meta:
        model = ZabbixServer
        fields = (
            'name',
            'description',
            'url',
            'token',
            'validate_certs',
        )
