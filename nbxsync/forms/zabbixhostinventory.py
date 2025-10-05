import logging
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, TagFilterField
from utilities.forms.rendering import FieldSet, TabbedGroups
from dcim.models import Device, VirtualDeviceContext
from virtualization.models import VirtualMachine

from nbxsync.choices import ZabbixHostInventoryModeChoices
from nbxsync.constants import ASSIGNMENT_TYPE_TO_FIELD_NBOBJS
from nbxsync.models import ZabbixHostInventory

__all__ = ('ZabbixHostInventoryForm', 'ZabbixHostInventoryFilterForm', 'ZabbixHostInventoryBulkEditForm')

logger = logging.getLogger(__name__)


class ZabbixHostInventoryForm(NetBoxModelForm):
    inventory_mode = forms.TypedChoiceField(choices=ZabbixHostInventoryModeChoices, coerce=int, initial=ZabbixHostInventoryModeChoices.MANUAL, label=_('Inventory mode'), required=True)
    # inventory_mode = forms.IntegerField(required=False)
    alias = forms.CharField(required=False, label=_('Alias'))
    asset_tag = forms.CharField(required=False, label=_('Asset tag'))
    chassis = forms.CharField(required=False, label=_('Chassis'))
    contact = forms.CharField(widget=forms.Textarea, required=False, label=_('Contact'))
    contract_number = forms.CharField(required=False, label=_('Contract number'))
    date_hw_decomm = forms.CharField(required=False, label=_('Date HW decommussioned'))
    date_hw_expiry = forms.CharField(required=False, label=_('Date HW maintenance expires'))
    date_hw_install = forms.CharField(required=False, label=_('Date HW installed'))
    date_hw_purchase = forms.CharField(required=False, label=_('Date HW purchased'))
    deployment_status = forms.CharField(required=False, label=_('Deployment status'))
    hardware = forms.CharField(required=False, label=_('Hardware'))
    hardware_full = forms.CharField(widget=forms.Textarea, required=False, label=_('Hardware (Full details)'))
    host_netmask = forms.CharField(required=False, label=_('Host subnet mask'))
    host_networks = forms.CharField(widget=forms.Textarea, required=False, label=_('Host networks'))
    host_router = forms.CharField(required=False, label=_('Host router'))
    hw_arch = forms.CharField(required=False, label=_('HW architecture'))
    installer_name = forms.CharField(required=False, label=_('Installer name'))
    location = forms.CharField(widget=forms.Textarea, required=False, label=_('Location'))
    location_lat = forms.CharField(required=False, label=_('Location latitude'))
    location_lon = forms.CharField(required=False, label=_('Location longitude'))
    macaddress_a = forms.CharField(required=False, label=_('MAC address A'))
    macaddress_b = forms.CharField(required=False, label=_('MAC address B'))
    model_field = forms.CharField(required=False, label=_('Model'))
    name = forms.CharField(required=False, label=_('Name'))
    notes = forms.CharField(widget=forms.Textarea, required=False, label=_('Notes'))
    oob_ip = forms.CharField(required=False, label=_('OOB IP address'))
    oob_netmask = forms.CharField(required=False, label=_('OOB subnet mask'))
    oob_router = forms.CharField(required=False, label=_('OOB router'))
    os = forms.CharField(required=False, label=_('OS'))
    os_full = forms.CharField(required=False, label=_('OS (Full details)'))
    os_short = forms.CharField(required=False, label=_('OS (Short)'))
    poc_1_cell = forms.CharField(required=False, label=_('Primary POC cell'))
    poc_1_email = forms.CharField(required=False, label=_('Primary POC email'))
    poc_1_name = forms.CharField(required=False, label=_('Primary POC name'))
    poc_1_notes = forms.CharField(widget=forms.Textarea, required=False, label=_('Primary POC notes'))
    poc_1_phone_a = forms.CharField(required=False, label=_('Primary POC phone A'))
    poc_1_phone_b = forms.CharField(required=False, label=_('Primary POC phone B'))
    poc_1_screen = forms.CharField(required=False, label=_('Primary POC screen name'))
    poc_2_cell = forms.CharField(required=False, label=_('Secondary POC cell'))
    poc_2_email = forms.CharField(required=False, label=_('Secondary POC email'))
    poc_2_name = forms.CharField(required=False, label=_('Secondary POC name'))
    poc_2_notes = forms.CharField(widget=forms.Textarea, required=False, label=_('Secondary POC notes'))
    poc_2_phone_a = forms.CharField(required=False, label=_('Secondary POC phone A'))
    poc_2_phone_b = forms.CharField(required=False, label=_('Secondary POC phone B'))
    poc_2_screen = forms.CharField(required=False, label=_('Secondary POC  screen name'))
    serialno_a = forms.CharField(required=False, label=_('Serial number A'))
    serialno_b = forms.CharField(required=False, label=_('Serial number B'))
    site_address_a = forms.CharField(required=False, label=_('Site address A'))
    site_address_b = forms.CharField(required=False, label=_('Site address B'))
    site_address_c = forms.CharField(required=False, label=_('Site address C'))

    device = DynamicModelChoiceField(queryset=Device.objects.all(), required=False, selector=True, label=_('Device'))
    virtualdevicecontext = DynamicModelChoiceField(queryset=VirtualDeviceContext.objects.all(), required=False, selector=True, label=_('Virtual Device Context'))
    virtualmachine = DynamicModelChoiceField(queryset=VirtualMachine.objects.all(), required=False, selector=True, label=_('Virtual Machine'))

    fieldsets = (
        FieldSet(
            'inventory_mode',
            'alias',
            'asset_tag',
            'chassis',
            'contact',
            'contract_number',
            'deployment_status',
            'installer_name',
            'vendor',
            name=_('General'),
        ),
        FieldSet(
            'hardware',
            'hardware_full',
            'model_field',
            'serialno_a',
            'serialno_b',
            'os',
            'os_full',
            'os_short',
            'software',
            'software_full',
            'software_app_a',
            'software_app_b',
            'software_app_c',
            'software_app_d',
            'software_app_e',
            name=_('Hardware & Software'),
        ),
        FieldSet(
            'date_hw_decomm',
            'date_hw_expiry',
            'date_hw_install',
            'date_hw_purchase',
            name=_('Lifecycle Dates'),
        ),
        FieldSet(
            'location',
            'location_lat',
            'location_lon',
            'site_address_a',
            'site_address_b',
            'site_address_c',
            'site_city',
            'site_state',
            'site_country',
            'site_zip',
            'site_rack',
            'site_notes',
            name=_('Location'),
        ),
        FieldSet(
            'host_netmask',
            'host_networks',
            'host_router',
            'oob_ip',
            'oob_netmask',
            'oob_router',
            name=_('Networking'),
        ),
        FieldSet(
            'macaddress_a',
            'macaddress_b',
            'hw_arch',
            name=_('Hardware Identifiers'),
        ),
        FieldSet(
            'poc_1_name',
            'poc_1_email',
            'poc_1_phone_a',
            'poc_1_phone_b',
            'poc_1_cell',
            'poc_1_screen',
            'poc_1_notes',
            name=_('Primary Contact'),
        ),
        FieldSet(
            'poc_2_name',
            'poc_2_email',
            'poc_2_phone_a',
            'poc_2_phone_b',
            'poc_2_cell',
            'poc_2_screen',
            'poc_2_notes',
            name=_('Secondary Contact'),
        ),
        FieldSet(
            'tag',
            'type',
            'type_full',
            'url_a',
            'url_b',
            'url_c',
            'name',
            'notes',
            name=_('Miscellaneous'),
        ),
        FieldSet(
            TabbedGroups(
                FieldSet('device', name=_('Device')),
                FieldSet('virtualdevicecotext', name=_('Virtual Device Context')),
                FieldSet('virtualmachine', name=_('Virtual Machine')),
            ),
            name=_('Assignment'),
        ),
    )

    class Meta:
        model = ZabbixHostInventory
        fields = (
            'inventory_mode',
            'alias',
            'asset_tag',
            'chassis',
            'contact',
            'contract_number',
            'deployment_status',
            'installer_name',
            'vendor',
            'hardware',
            'hardware_full',
            'model_field',
            'serialno_a',
            'serialno_b',
            'os',
            'os_full',
            'os_short',
            'software',
            'software_full',
            'software_app_a',
            'software_app_b',
            'software_app_c',
            'software_app_d',
            'software_app_e',
            'date_hw_decomm',
            'date_hw_expiry',
            'date_hw_install',
            'date_hw_purchase',
            'location',
            'location_lat',
            'location_lon',
            'site_address_a',
            'site_address_b',
            'site_address_c',
            'site_city',
            'site_state',
            'site_country',
            'site_zip',
            'site_rack',
            'site_notes',
            'host_netmask',
            'host_networks',
            'host_router',
            'oob_ip',
            'oob_netmask',
            'oob_router',
            'macaddress_a',
            'macaddress_b',
            'hw_arch',
            'poc_1_name',
            'poc_1_email',
            'poc_1_phone_a',
            'poc_1_phone_b',
            'poc_1_cell',
            'poc_1_screen',
            'poc_1_notes',
            'poc_2_name',
            'poc_2_email',
            'poc_2_phone_a',
            'poc_2_phone_b',
            'poc_2_cell',
            'poc_2_screen',
            'poc_2_notes',
            'tag',
            'type',
            'type_full',
            'url_a',
            'url_b',
            'url_c',
            'name',
            'notes',
            'device',
            'virtualmachine',
        )

    @property
    def assignable_fields(self):
        return list(ASSIGNMENT_TYPE_TO_FIELD_NBOBJS.values())

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        initial = kwargs.get('initial', {}).copy()

        if instance and instance.assigned_object:
            for model_class, field in ASSIGNMENT_TYPE_TO_FIELD_NBOBJS.items():
                if isinstance(instance.assigned_object, model_class):
                    initial[field] = instance.assigned_object
                    break

        elif 'assigned_object_type' in initial and 'assigned_object_id' in initial:
            try:
                content_type = ContentType.objects.get(pk=initial['assigned_object_type'])
                obj = content_type.get_object_for_this_type(pk=initial['assigned_object_id'])
                for model_class, field in ASSIGNMENT_TYPE_TO_FIELD_NBOBJS.items():
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
        selected = [field for field in self.assignable_fields if self.cleaned_data.get(field)]
        if len(selected) > 1:
            raise forms.ValidationError({selected[1]: _('Zabbox Host Inventory can only be assigned to one object.')})
        elif selected:
            self.instance.assigned_object = self.cleaned_data[selected[0]]
        else:
            self.instance.assigned_object = None


class ZabbixHostInventoryFilterForm(NetBoxModelFilterSetForm):
    model = ZabbixHostInventory

    fieldsets = (
        FieldSet('q', 'filter_id', name=_('Search')),
        FieldSet('inventory_mode', 'alias', 'asset_tag', 'chassis', 'contract_number', name=_('General')),
        FieldSet('hardware', 'hardware_full', 'model_field', 'os', 'software', name=_('Hardware & Software')),
        FieldSet('date_hw_decomm', 'date_hw_expiry', 'date_hw_install', 'date_hw_purchase', name=_('Lifecycle')),
        FieldSet('host_netmask', 'oob_ip', 'oob_netmask', name=_('Networking')),
        FieldSet('location', 'site_city', 'site_state', 'site_country', 'site_zip', name=_('Location')),
        FieldSet('poc_1_name', 'poc_1_email', 'poc_2_name', 'poc_2_email', name=_('Contacts')),
        FieldSet('type', 'vendor', 'tag', name=_('Miscellaneous')),
    )

    tag = TagFilterField(model)


class ZabbixHostInventoryBulkEditForm(NetBoxModelBulkEditForm):
    model = ZabbixHostInventory

    inventory_mode = forms.IntegerField(required=False)
    alias = forms.CharField(required=False, label=_('Alias'))
    asset_tag = forms.CharField(required=False, label=_('Asset tag'))
    chassis = forms.CharField(required=False, label=_('Chassis'))
    contact = forms.CharField(widget=forms.Textarea, required=False, label=_('Contact'))
    contract_number = forms.CharField(required=False, label=_('Contract number'))
    date_hw_decomm = forms.CharField(required=False, label=_('Date HW decommussioned'))
    date_hw_expiry = forms.CharField(required=False, label=_('Date HW maintenance expires'))
    date_hw_install = forms.CharField(required=False, label=_('Date HW installed'))
    date_hw_purchase = forms.CharField(required=False, label=_('Date HW purchased'))
    deployment_status = forms.CharField(required=False, label=_('Deployment status'))
    hardware = forms.CharField(required=False, label=_('Hardware'))
    hardware_full = forms.CharField(widget=forms.Textarea, required=False, label=_('Hardware (Full details)'))
    host_netmask = forms.CharField(required=False, label=_('Host subnet mask'))
    host_networks = forms.CharField(widget=forms.Textarea, required=False, label=_('Host networks'))
    host_router = forms.CharField(required=False, label=_('Host router'))
    hw_arch = forms.CharField(required=False, label=_('HW architecture'))
    installer_name = forms.CharField(required=False, label=_('Installer name'))
    location = forms.CharField(widget=forms.Textarea, required=False, label=_('Location'))
    location_lat = forms.CharField(required=False, label=_('Location latitude'))
    location_lon = forms.CharField(required=False, label=_('Location longitude'))
    macaddress_a = forms.CharField(required=False, label=_('MAC address A'))
    macaddress_b = forms.CharField(required=False, label=_('MAC address B'))
    model_field = forms.CharField(required=False, label=_('Model'))
    name = forms.CharField(required=False, label=_('Name'))
    notes = forms.CharField(widget=forms.Textarea, required=False, label=_('Notes'))
    oob_ip = forms.CharField(required=False, label=_('OOB IP address'))
    oob_netmask = forms.CharField(required=False, label=_('OOB subnet mask'))
    oob_router = forms.CharField(required=False, label=_('OOB router'))
    os = forms.CharField(required=False, label=_('OS'))
    os_full = forms.CharField(required=False, label=_('OS (Full details)'))
    os_short = forms.CharField(required=False, label=_('OS (Short)'))
    poc_1_cell = forms.CharField(required=False, label=_('Primary POC cell'))
    poc_1_email = forms.CharField(required=False, label=_('Primary POC email'))
    poc_1_name = forms.CharField(required=False, label=_('Primary POC name'))
    poc_1_notes = forms.CharField(widget=forms.Textarea, required=False, label=_('Primary POC notes'))
    poc_1_phone_a = forms.CharField(required=False, label=_('Primary POC phone A'))
    poc_1_phone_b = forms.CharField(required=False, label=_('Primary POC phone B'))
    poc_1_screen = forms.CharField(required=False, label=_('Primary POC screen name'))
    poc_2_cell = forms.CharField(required=False, label=_('Secondary POC cell'))
    poc_2_email = forms.CharField(required=False, label=_('Secondary POC email'))
    poc_2_name = forms.CharField(required=False, label=_('Secondary POC name'))
    poc_2_notes = forms.CharField(widget=forms.Textarea, required=False, label=_('Secondary POC notes'))
    poc_2_phone_a = forms.CharField(required=False, label=_('Secondary POC phone A'))
    poc_2_phone_b = forms.CharField(required=False, label=_('Secondary POC phone B'))
    poc_2_screen = forms.CharField(required=False, label=_('Secondary POC  screen name'))
    serialno_a = forms.CharField(required=False, label=_('Serial number A'))
    serialno_b = forms.CharField(required=False, label=_('Serial number B'))
    site_address_a = forms.CharField(required=False, label=_('Site address A'))
    site_address_b = forms.CharField(required=False, label=_('Site address B'))
    site_address_c = forms.CharField(required=False, label=_('Site address C'))
    site_city = forms.CharField(required=False, label=_('Site city'))
    site_country = forms.CharField(required=False, label=_('Site country'))
    site_notes = forms.CharField(widget=forms.Textarea, required=False, label=_('Site notes'))
    site_rack = forms.CharField(required=False, label=_('Site rack location'))
    site_state = forms.CharField(required=False, label=_('Site state / province'))
    site_zip = forms.CharField(required=False, label=_('Site ZIP / postal'))
    software = forms.CharField(required=False, label=_('Software'))
    software_app_a = forms.CharField(required=False, label=_('Software application A'))
    software_app_b = forms.CharField(required=False, label=_('Software application B'))
    software_app_c = forms.CharField(required=False, label=_('Software application C'))
    software_app_d = forms.CharField(required=False, label=_('Software application D'))
    software_app_e = forms.CharField(required=False, label=_('Software application E'))
    software_full = forms.CharField(widget=forms.Textarea, required=False, label=_('Software (Full details)'))
    tag = forms.CharField(required=False, label=_('Tag'))
    type = forms.CharField(required=False, label=_('Type'))
    type_full = forms.CharField(required=False, label=_('Type (Full details)'))
    url_a = forms.CharField(required=False, label=_('URL A'))
    url_b = forms.CharField(required=False, label=_('URL B'))
    url_c = forms.CharField(required=False, label=_('URL C'))
    vendor = forms.CharField(required=False, label=_('Vendor'))

    fieldsets = (
        FieldSet('inventory_mode', 'alias', 'asset_tag', 'chassis', 'contract_number', name=_('General')),
        FieldSet('hardware', 'hardware_full', 'model_field', 'os', 'software', name=_('Hardware & Software')),
        FieldSet('date_hw_decomm', 'date_hw_expiry', 'date_hw_install', 'date_hw_purchase', name=_('Lifecycle')),
        FieldSet('host_netmask', 'oob_ip', 'oob_netmask', name=_('Networking')),
        FieldSet('location', 'site_city', 'site_state', 'site_country', 'site_zip', name=_('Location')),
        FieldSet('poc_1_name', 'poc_1_email', 'poc_2_name', 'poc_2_email', name=_('Contacts')),
        FieldSet('type', 'vendor', 'tag', name=_('Miscellaneous')),
    )

    nullable_fields = ()
