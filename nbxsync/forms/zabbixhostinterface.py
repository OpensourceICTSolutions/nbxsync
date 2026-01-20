import logging
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, TagFilterField
from utilities.forms.rendering import FieldSet, TabbedGroups
from dcim.models import Device, VirtualDeviceContext
from virtualization.models import VirtualMachine
from ipam.models import IPAddress

from nbxsync.choices import IPMIAuthTypeChoices, IPMIPrivilegeChoices, ZabbixHostInterfaceTypeChoices, ZabbixInterfaceTypeChoices, ZabbixInterfaceUseChoices, ZabbixTLSChoices
from nbxsync.constants import ASSIGNMENT_TYPE_TO_FIELD, ASSIGNMENT_TYPE_TO_FIELD_NBOBJS
from nbxsync.models import ZabbixHostInterface, ZabbixServer, ZabbixServerAssignment, ZabbixConfigurationGroup
from nbxsync.models.zabbixproxy import default_tls_accept

__all__ = ('ZabbixHostInterfaceForm', 'ZabbixHostInterfaceFilterForm', 'ZabbixHostInterfaceBulkEditForm')
logger = logging.getLogger(__name__)


class ZabbixHostInterfaceForm(NetBoxModelForm):
    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=True, selector=True, label=_('Zabbix Server'))
    ip = DynamicModelChoiceField(queryset=IPAddress.objects.all(), required=False, selector=True, label=_('IP Address'))

    device = DynamicModelChoiceField(queryset=Device.objects.all(), required=False, selector=True, label=_('Device'))
    virtualdevicecontext = DynamicModelChoiceField(queryset=VirtualDeviceContext.objects.all(), required=False, selector=True, label=_('Virtual Device Context'))
    virtualmachine = DynamicModelChoiceField(queryset=VirtualMachine.objects.all(), required=False, selector=True, label=_('Virtual Machine'))
    zabbixconfigurationgroup = DynamicModelChoiceField(queryset=ZabbixConfigurationGroup.objects.all(), required=False, selector=True, label=_('Zabbix Configuration Group'))

    port = forms.IntegerField(required=True, label=_('Port number'), help_text=_('10050 for Agent'))

    tls_connect = forms.TypedChoiceField(choices=ZabbixTLSChoices, required=False, coerce=int, label=_('Connections to agent'))
    tls_accept = forms.TypedMultipleChoiceField(choices=ZabbixTLSChoices, required=False, coerce=int, initial=default_tls_accept, label=_('Connections from agent'))
    tls_psk_identity = forms.CharField(required=False, label=_('PSK identity'))
    tls_psk = forms.CharField(required=False, label=_('PSK'), widget=forms.PasswordInput(render_value=True))
    tls_issuer = forms.CharField(required=False, label=_('Issuer'))
    tls_subject = forms.CharField(required=False, label=_('Subject'))

    ipmi_authtype = forms.TypedChoiceField(choices=IPMIAuthTypeChoices, required=False, coerce=int, empty_value=None, initial=-1, label=_('Auth type'))
    ipmi_privilege = forms.TypedChoiceField(choices=IPMIPrivilegeChoices, required=False, coerce=int, empty_value=None, initial=2, label=_('Privilege'))

    ipmi_password = forms.CharField(required=False, label=_('Password'), widget=forms.PasswordInput(render_value=True))
    snmp_pushcommunity = forms.BooleanField(required=False, label=_('Push SNMP Community'), help_text=_('Should the SNMP Credentials be pushed from NetBox or should the existing Zabbix macro be used?'))
    snmpv3_authentication_passphrase = forms.CharField(required=False, label=_('Authentication passphrase'), widget=forms.PasswordInput(render_value=True))
    snmpv3_privacy_passphrase = forms.CharField(required=False, label=_('Privacy passphrase '), widget=forms.PasswordInput(render_value=True))

    fieldsets = (
        FieldSet(
            'zabbixserver',
            'type',
            'dns',
            'port',
            'useip',
            'interface_type',
            'ip',
            'device',
            'virtualdevicecontext',
            'virtualmachine',
            'zabbixconfigurationgroup',
            name=_('Zabbix Host Interface'),
        ),
        FieldSet(
            TabbedGroups(
                FieldSet('device', name=_('Device')),
                FieldSet('virtualdevicecontext', name=_('Virtual Device Context')),
                FieldSet('virtualmachine', name=_('Virtual Machine')),
                FieldSet('zabbixconfigurationgroup', name=_('Zabbix Configuration Group')),
            ),
            name=_('Assignment'),
        ),
        FieldSet(
            'tls_connect',
            'tls_accept',
            'tls_issuer',
            'tls_subject',
            'tls_psk_identity',
            'tls_psk',
            name=_('TLS Configuration'),
        ),
        FieldSet(
            'snmp_version',
            'snmp_usebulk',
            'snmp_pushcommunitysnmpv3_context_name',
            'snmpv3_security_name',
            'snmpv3_security_level',
            'snmpv3_authentication_passphrase',
            'snmpv3_authentication_protocol',
            'snmpv3_privacy_passphrase',
            'snmpv3_privacy_protocol',
            name=_('SNMP Configuration'),
        ),
        FieldSet(
            'ipmi_authtype',
            'ipmi_password',
            'ipmi_privilege',
            'ipmi_username',
            name=_('IPMI Configuration'),
        ),
    )

    class Meta:
        model = ZabbixHostInterface
        fields = (
            'zabbixserver',
            'type',
            'dns',
            'port',
            'useip',
            'interface_type',
            'ip',
            'device',
            'virtualdevicecontext',
            'virtualmachine',
            'zabbixconfigurationgroup',
            'tls_connect',
            'tls_accept',
            'tls_issuer',
            'tls_subject',
            'tls_psk_identity',
            'tls_psk',
            'snmp_version',
            'snmp_usebulk',
            'snmp_community',
            'snmp_pushcommunity',
            'snmpv3_context_name',
            'snmpv3_security_name',
            'snmpv3_security_level',
            'snmpv3_authentication_passphrase',
            'snmpv3_authentication_protocol',
            'snmpv3_privacy_passphrase',
            'snmpv3_privacy_protocol',
            'ipmi_authtype',
            'ipmi_password',
            'ipmi_privilege',
            'ipmi_username',
        )

    @property
    def assignable_fields(self):
        return list(ASSIGNMENT_TYPE_TO_FIELD_NBOBJS.values())

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

            # If there is only 1 ZabbixServerAssignment, set it as the default
            # If there are more, exceptions will be thrown: catch them (and ignore!)
            try:
                assignment = ZabbixServerAssignment.objects.get(assigned_object_type=initial['assigned_object_type'], assigned_object_id=initial['assigned_object_id'])
                initial['zabbixserver'] = assignment.id
            except ZabbixServerAssignment.DoesNotExist:
                pass  # no assignment
            except ZabbixServerAssignment.MultipleObjectsReturned:
                pass  # more than one found, wont do anything

        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()

        selected_objects = [field for field in self.assignable_fields if self.cleaned_data.get(field)]

        if len(selected_objects) > 1:
            raise forms.ValidationError({selected_objects[1]: _('An Host Interface can only be assigned to a single object.')})
        elif selected_objects:
            self.instance.assigned_object = self.cleaned_data[selected_objects[0]]


class ZabbixHostInterfaceFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixHostInterface

    zabbixserver = DynamicModelChoiceField(queryset=ZabbixServer.objects.all(), required=False, selector=True, label=_('Zabbix Server'))
    device = DynamicModelChoiceField(queryset=Device.objects.all(), required=False, selector=True, label=_('Device'))
    virtualdevicecontext = DynamicModelChoiceField(queryset=VirtualDeviceContext.objects.all(), required=False, selector=True, label=_('Virtual Device Context'))
    virtualmachine = DynamicModelChoiceField(queryset=VirtualMachine.objects.all(), required=False, selector=True, label=_('Virtual Machine'))
    zabbixconfigurationgroup = DynamicModelChoiceField(queryset=ZabbixConfigurationGroup.objects.all(), required=False, selector=True, label=_('Zabbix Configuration Group'))

    fieldsets = (
        FieldSet('q', 'filter_id'),
        FieldSet(
            'zabbixserver',
            'type',
            'dns',
            'port',
            'useip',
            'interface_type',
            'ip',
            'device',
            'virtualdevicecontext',
            'virtualmachine',
            'zabbixconfigurationgroup',
            name=_('Zabbix Host Interface'),
        ),
    )

    tag = TagFilterField(model)


class ZabbixHostInterfaceBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixHostInterface

    type = forms.ChoiceField(label=_('Host Interface Type'), choices=ZabbixHostInterfaceTypeChoices, required=False)
    useip = forms.ChoiceField(label=_('Use IP'), choices=ZabbixInterfaceUseChoices, required=False)
    interface_type = forms.ChoiceField(label=_('Interface Type'), choices=ZabbixInterfaceTypeChoices, required=False)
    ip = forms.ModelChoiceField(queryset=IPAddress.objects.all(), required=False, label=_('IP Address'))
    dns = forms.CharField(label=_('DNS'), required=False, max_length=1200)
    port = forms.CharField(label=_('Port'), required=False, max_length=10)

    fieldsets = (
        FieldSet(
            'type',
            'useip',
            'interface_type',
            'ip',
            'dns',
            'port',
            name=_('Host Interface'),
        ),
    )

    nullable_fields = ('ip', 'dns', 'port')
