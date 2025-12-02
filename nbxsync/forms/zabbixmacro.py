import logging
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, TagFilterField
from utilities.forms.rendering import FieldSet, TabbedGroups

from nbxsync.choices import ZabbixMacroTypeChoices
from nbxsync.constants import ASSIGNMENT_TYPE_TO_FIELD
from nbxsync.models import ZabbixMacro, ZabbixServer, ZabbixTemplate

__all__ = ('ZabbixMacroForm', 'ZabbixMacroFilterForm', 'ZabbixMacroBulkEditForm')
logger = logging.getLogger(__name__)


class ZabbixMacroForm(NetBoxModelForm):
    macro = forms.CharField(label=_('Macro'), max_length=200, required=True)
    type = forms.ChoiceField(label=_('Macro Type'), choices=ZabbixMacroTypeChoices.choices)
    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=False, selector=True, label=_('Zabbix Server'))
    zabbixtemplate = DynamicModelChoiceField(queryset=ZabbixTemplate.objects.all(), required=False, selector=True, label=_('Zabbix Template'), query_params={'zabbixserver_id': '$zabbixserver'})

    fieldsets = (
        FieldSet('macro', 'description', 'type', 'value', name=_('Generic')),
        FieldSet(
            TabbedGroups(
                FieldSet('zabbixserver', name=_('Zabbix Server')),
                FieldSet('zabbixtemplate', name=_('Zabbix Template')),
            ),
            name=_('Assignment'),
        ),
    )

    class Meta:
        model = ZabbixMacro
        fields = (
            'macro',
            'value',
            'description',
            'type',
            'zabbixserver',
            'zabbixtemplate',
        )

    @property
    def assignable_fields(self):
        return list(ASSIGNMENT_TYPE_TO_FIELD.values())

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        initial = kwargs.get('initial', {}).copy()

        if instance and instance.assigned_object:
            for model_class, field in ASSIGNMENT_TYPE_TO_FIELD.items():
                if isinstance(instance.assigned_object, model_class):
                    initial[field] = instance.assigned_object
                    break

        elif 'assigned_object_type' in initial and 'assigned_object_id' in initial:
            try:
                content_type = ContentType.objects.get(pk=initial['assigned_object_type'])
                obj = content_type.get_object_for_this_type(pk=initial['assigned_object_id'])

                for model_class, field in ASSIGNMENT_TYPE_TO_FIELD.items():
                    if isinstance(obj, model_class):
                        initial[field] = obj.pk
                        break

            except Exception as e:
                logger.debug('Prefill error (assigned_object_type=%s, assigned_object_id=%s): %s', initial.get('assigned_object_type'), initial.get('assigned_object_id'), e)
                pass

        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()

        selected_objects = [field for field in self.assignable_fields if self.cleaned_data.get(field)]

        if len(selected_objects) > 1:
            raise forms.ValidationError({selected_objects[1]: _('A Macro can only be assigned to a single object.')})
        elif selected_objects:
            self.instance.assigned_object = self.cleaned_data[selected_objects[0]]
        else:
            self.instance.assigned_object = None


class ZabbixMacroFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixMacro

    description = forms.CharField(label=_('Macro'), max_length=1024, required=False)
    hostmacroid = forms.IntegerField(label=_('Host Macro ID'), required=False)
    type = forms.ChoiceField(choices=ZabbixMacroTypeChoices.choices, required=False)

    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet('macro', 'value', 'description', 'type', 'hostmacroid', name=_('Zabbix Macro')),
    )

    tag = TagFilterField(model)


class ZabbixMacroBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixMacro
    macro = forms.CharField(label=_('Macro'), max_length=200, required=False)
    description = forms.CharField(label=_('Macro'), max_length=1024, required=False)
    hostmacroid = forms.IntegerField(label=_('Host Macro ID'), required=False)
    type = forms.ChoiceField(choices=ZabbixMacroTypeChoices.choices, required=False)

    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=False, selector=True, label=_('Zabbix Server'))
    zabbixtemplate = DynamicModelChoiceField(queryset=ZabbixTemplate.objects.all(), required=False, selector=True, label=_('Zabbix Template'), query_params={'zabbixserver_id': '$zabbixserver'})

    fieldsets = (
        FieldSet(
            'macro',
            'hostmacroid',
            'value',
            'description',
            'type',
            'zabbixserver',
            'zabbixtemplate',
        ),
    )
    nullable_fields = ()
