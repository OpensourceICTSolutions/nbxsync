from django import forms
from django.utils.translation import gettext as _

from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField
from utilities.forms.rendering import FieldSet

from dcim.models import Manufacturer

from nbxsync.models import ZabbixHostgroup, ZabbixServer, ZabbixTag, ZabbixTemplate, ZabbixTemplateRule

__all__ = (
    'ZabbixTemplateRuleForm',
    'ZabbixTemplateRuleFilterForm',
    'ZabbixTemplateRuleBulkEditForm',
)


class ZabbixTemplateRuleForm(NetBoxModelForm):
    # Form-only filter so NetBox APISelect can cascade template/hostgroup choices.
    # Not persisted on ZabbixTemplateRule (server is implied by the template).
    zabbixserver = DynamicModelChoiceField(
        queryset=ZabbixServer.objects.all(),
        required=False,
        selector=True,
        label=_('Zabbix Server'),
        help_text=_('Filters the template and hostgroup lists. Not stored on the rule.'),
    )
    zabbixtemplate = DynamicModelChoiceField(
        queryset=ZabbixTemplate.objects.all(),
        selector=True,
        label=_('Zabbix Template'),
        query_params={'zabbixserver_id': '$zabbixserver'},
    )
    zabbixhostgroup = DynamicModelChoiceField(
        queryset=ZabbixHostgroup.objects.all(),
        required=False,
        selector=True,
        label=_('Zabbix Hostgroup'),
        query_params={'zabbixserver_id': '$zabbixserver'},
    )
    zabbixtag = DynamicModelChoiceField(queryset=ZabbixTag.objects.all(), required=False, selector=True, label=_('Zabbix Tag'))
    manufacturer = DynamicModelChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
        selector=True,
        label=_('Manufacturer'),
        help_text=_('Optional. When set, only Devices whose device type manufacturer matches. Empty = any. VMs fail closed.'),
    )

    class Meta:
        model = ZabbixTemplateRule
        fields = (
            'name',
            'description',
            'pattern',
            'role_pattern',
            'require_tags',
            'manufacturer',
            'zabbixtemplate',
            'zabbixhostgroup',
            'zabbixtag',
            'enabled',
            'priority',
        )

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        initial = kwargs.get('initial', {}).copy()
        if instance and getattr(instance, 'zabbixtemplate_id', None):
            initial.setdefault('zabbixserver', instance.zabbixtemplate.zabbixserver_id)
        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)
        # zabbixserver is form-only; keep it next to the fields it filters.
        # Preserve any fields NetBoxModelForm added after Meta.fields (custom
        # fields, tags, changelog_message, …) — dropping them silently breaks
        # create/edit tests and CF persistence in the UI.
        preferred = (
            'name',
            'description',
            'pattern',
            'role_pattern',
            'require_tags',
            'manufacturer',
            'zabbixserver',
            'zabbixtemplate',
            'zabbixhostgroup',
            'zabbixtag',
            'enabled',
            'priority',
        )
        preferred_set = set(preferred)
        ordered = [(name, self.fields[name]) for name in preferred if name in self.fields]
        remaining = [(name, field) for name, field in self.fields.items() if name not in preferred_set]
        self.fields = type(self.fields)(ordered + remaining)


class ZabbixTemplateRuleFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixTemplateRule
    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet('name', 'description', 'pattern', 'role_pattern', 'require_tags', 'manufacturer', 'enabled', name=_('Zabbix Template Rule')),
    )

    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False, label=_('Manufacturer'))
    enabled = forms.NullBooleanField(required=False, label=_('Enabled'))


class ZabbixTemplateRuleBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixTemplateRule

    description = forms.CharField(label=_('Description'), max_length=200, required=False)
    pattern = forms.CharField(label=_('Pattern'), max_length=500, required=False)
    role_pattern = forms.CharField(label=_('Role Pattern'), max_length=500, required=False)
    require_tags = forms.CharField(label=_('Require Tags'), max_length=200, required=False)
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False, selector=True, label=_('Manufacturer'))
    zabbixtemplate = forms.ModelChoiceField(queryset=ZabbixTemplate.objects.all(), required=False, label=_('Zabbix Template'))
    zabbixhostgroup = forms.ModelChoiceField(queryset=ZabbixHostgroup.objects.all(), required=False, label=_('Zabbix Hostgroup'))
    zabbixtag = forms.ModelChoiceField(queryset=ZabbixTag.objects.all(), required=False, label=_('Zabbix Tag'))
    enabled = forms.NullBooleanField(required=False, label=_('Enabled'))
    priority = forms.IntegerField(required=False, label=_('Priority'))

    fieldsets = (
        FieldSet(
            'description',
            'pattern',
            'role_pattern',
            'require_tags',
            'manufacturer',
            'zabbixtemplate',
            'zabbixhostgroup',
            'zabbixtag',
            'enabled',
            'priority',
            name=_('Zabbix Template Rule'),
        ),
    )
    nullable_fields = ('description', 'role_pattern', 'require_tags', 'manufacturer', 'zabbixhostgroup', 'zabbixtag')
