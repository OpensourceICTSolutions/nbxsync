from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from jinja2 import TemplateError, TemplateSyntaxError, UndefinedError

from netbox.models import NetBoxModel
from utilities.jinja2 import render_jinja2

from nbxsync.choices import ZabbixHostInventoryModeChoices
from nbxsync.constants import DEVICE_OR_VM_ASSIGNMENT_MODELS

__all__ = ('ZabbixHostInventory',)


class ZabbixHostInventory(NetBoxModel):
    inventory_mode = models.IntegerField(choices=ZabbixHostInventoryModeChoices, default=ZabbixHostInventoryModeChoices.MANUAL, verbose_name=_('Inventory mode'))
    alias = models.CharField(max_length=128, blank=True, verbose_name=_('Alias'))
    asset_tag = models.CharField(max_length=64, blank=True, verbose_name=_('Asset tag'))
    chassis = models.CharField(max_length=64, blank=True, verbose_name=_('Chassis'))
    contact = models.TextField(blank=True, verbose_name=_('Contact'))
    contract_number = models.CharField(max_length=64, blank=True, verbose_name=_('Contract number'))
    date_hw_decomm = models.CharField(max_length=64, blank=True, verbose_name=_('Date HW decommussioned'))
    date_hw_expiry = models.CharField(max_length=64, blank=True, verbose_name=_('Date HW maintenance expires'))
    date_hw_install = models.CharField(max_length=64, blank=True, verbose_name=_('Date HW installed'))
    date_hw_purchase = models.CharField(max_length=64, blank=True, verbose_name=_('Date HW purchased'))
    deployment_status = models.CharField(max_length=64, blank=True, verbose_name=_('Deployment status'))
    hardware = models.CharField(max_length=255, blank=True, verbose_name=_('Hardware'))
    hardware_full = models.TextField(blank=True, verbose_name=_('Hardware (Full details)'))
    host_netmask = models.CharField(max_length=39, blank=True, verbose_name=_('Host subnet mask'))
    host_networks = models.TextField(blank=True, verbose_name=_('Host networks'))
    host_router = models.CharField(max_length=39, blank=True, verbose_name=_('Host router'))
    hw_arch = models.CharField(max_length=32, blank=True, verbose_name=_('HW architecture'))
    installer_name = models.CharField(max_length=64, blank=True, verbose_name=_('Installer name'))
    location = models.TextField(blank=True, verbose_name=_('Location '))
    location_lat = models.CharField(max_length=30, blank=True, verbose_name=_('Location latitude'))
    location_lon = models.CharField(max_length=30, blank=True, verbose_name=_('Location longitude'))
    macaddress_a = models.CharField(max_length=64, blank=True, verbose_name=_('MAC address A'))
    macaddress_b = models.CharField(max_length=64, blank=True, verbose_name=_('MAC address B'))
    model_field = models.CharField(max_length=64, blank=True, verbose_name=_('Model'))
    name = models.CharField(max_length=128, blank=True, verbose_name=_('Name'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    oob_ip = models.CharField(max_length=39, blank=True, verbose_name=_('OOB IP address'))
    oob_netmask = models.CharField(max_length=39, blank=True, verbose_name=_('OOB subnet mask'))
    oob_router = models.CharField(max_length=39, blank=True, verbose_name=_('OOB router'))
    os = models.CharField(max_length=128, blank=True, verbose_name=_('OS'))
    os_full = models.CharField(max_length=255, blank=True, verbose_name=_('OS (Full details)'))
    os_short = models.CharField(max_length=128, blank=True, verbose_name=_('OS (Short)'))
    poc_1_cell = models.CharField(max_length=64, blank=True, verbose_name=_('Primary POC cell'))
    poc_1_email = models.CharField(max_length=128, blank=True, verbose_name=_('Primary POC email'))
    poc_1_name = models.CharField(max_length=128, blank=True, verbose_name=_('Primary POC name'))
    poc_1_notes = models.TextField(blank=True, verbose_name=_('Primary POC notes'))
    poc_1_phone_a = models.CharField(max_length=64, blank=True, verbose_name=_('Primary POC phone A'))
    poc_1_phone_b = models.CharField(max_length=64, blank=True, verbose_name=_('Primary POC phone B'))
    poc_1_screen = models.CharField(max_length=64, blank=True, verbose_name=_('Primary POC screen name'))
    poc_2_cell = models.CharField(max_length=64, blank=True, verbose_name=_('Secondary POC cell'))
    poc_2_email = models.CharField(max_length=128, blank=True, verbose_name=_('Secondary POC email'))
    poc_2_name = models.CharField(max_length=128, blank=True, verbose_name=_('Secondary POC name'))
    poc_2_notes = models.TextField(blank=True, verbose_name=_('Secondary POC notes'))
    poc_2_phone_a = models.CharField(max_length=64, blank=True, verbose_name=_('Secondary POC phone A'))
    poc_2_phone_b = models.CharField(max_length=64, blank=True, verbose_name=_('Secondary POC phone B'))
    poc_2_screen = models.CharField(max_length=64, blank=True, verbose_name=_('Secondary POC  screen name'))
    serialno_a = models.CharField(max_length=64, blank=True, verbose_name=_('Serial number A'))
    serialno_b = models.CharField(max_length=64, blank=True, verbose_name=_('Serial number B'))
    site_address_a = models.CharField(max_length=128, blank=True, verbose_name=_('Site address A'))
    site_address_b = models.CharField(max_length=128, blank=True, verbose_name=_('Site address B'))
    site_address_c = models.CharField(max_length=128, blank=True, verbose_name=_('Site address C'))
    site_city = models.CharField(max_length=128, blank=True, verbose_name=_('Site city'))
    site_country = models.CharField(max_length=64, blank=True, verbose_name=_('Site country'))
    site_notes = models.TextField(blank=True, verbose_name=_('Site notes'))
    site_rack = models.CharField(max_length=128, blank=True, verbose_name=_('Site rack location'))
    site_state = models.CharField(max_length=64, blank=True, verbose_name=_('Site state / province'))
    site_zip = models.CharField(max_length=64, blank=True, verbose_name=_('Site ZIP / postal'))
    software = models.CharField(max_length=255, blank=True, verbose_name=_('Software'))
    software_app_a = models.CharField(max_length=64, blank=True, verbose_name=_('Software application A'))
    software_app_b = models.CharField(max_length=64, blank=True, verbose_name=_('Software application B'))
    software_app_c = models.CharField(max_length=64, blank=True, verbose_name=_('Software application C'))
    software_app_d = models.CharField(max_length=64, blank=True, verbose_name=_('Software application D'))
    software_app_e = models.CharField(max_length=64, blank=True, verbose_name=_('Software application E'))
    software_full = models.TextField(blank=True, verbose_name=_('Software (Full details)'))
    tag = models.CharField(max_length=64, blank=True, verbose_name=_('Tag'))
    type = models.CharField(max_length=64, blank=True, verbose_name=_('Type'))
    type_full = models.CharField(max_length=64, blank=True, verbose_name=_('Type (Full details)'))
    url_a = models.CharField(max_length=2048, blank=True, verbose_name=_('URL A'))
    url_b = models.CharField(max_length=2048, blank=True, verbose_name=_('URL B'))
    url_c = models.CharField(max_length=2048, blank=True, verbose_name=_('URL C'))
    vendor = models.CharField(max_length=64, blank=True, verbose_name=_('Vendor'))

    assigned_object_type = models.ForeignKey(to=ContentType, limit_choices_to=DEVICE_OR_VM_ASSIGNMENT_MODELS, on_delete=models.CASCADE, related_name='+', blank=True, null=True)
    assigned_object_id = models.PositiveBigIntegerField(blank=True, null=True)
    assigned_object = GenericForeignKey(ct_field='assigned_object_type', fk_field='assigned_object_id')

    class Meta:
        verbose_name = 'Zabbix Host Inventory'
        verbose_name_plural = 'Zabbix Host Inventories'
        ordering = ('-created',)

        constraints = [
            models.UniqueConstraint(
                fields=['assigned_object_type', 'assigned_object_id'],
                name='%(app_label)s_%(class)s_unique_assigned_object',
                violation_error_message='Only one inventory entry is allowed per assigned object.',
            )
        ]

    def get_context(self, **extra_context):
        """
        Provide the rendering context for Jinja2 templates.
        Override or extend as needed.
        """
        context = {'object': self.assigned_object}
        context.update(extra_context)
        return context

    def get_inventory_mode(self):
        return ZabbixHostInventoryModeChoices(self.inventory_mode).label

    def render_field(self, field_name, **context):
        """
        Render a single field using Jinja2.
        Returns a tuple of (rendered_value, success_flag).
        """
        template_field = getattr(self, field_name, '')
        try:
            rendered = render_jinja2(template_field, self.get_context(**context))
            rendered = rendered.replace('\r\n', '\n')

            max_len = self._MAX_LENGTHS.get(field_name)
            if max_len is not None and len(rendered) > max_len:
                rendered = rendered[:max_len]

            return rendered, True

        except (TemplateSyntaxError, UndefinedError, TemplateError) as err:
            pass
        except Exception as err:
            pass
        return '', False

    def render_all_fields(self, **context):
        """
        Render all string-based fields that might contain templates.
        Returns a dict mapping field names to (rendered_value, success).
        """
        rendered = {}
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                field_name = field.name
                rendered[field_name] = self.render_field(field_name, **context)
        return rendered

    def clean(self):
        super().clean()
        if self.assigned_object_type is None or self.assigned_object_id is None:
            raise ValidationError('An assigned object must be provided')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Host Inventory of {self.assigned_object.name}'

    _MAX_LENGTHS = {
        'alias': 128,
        'asset_tag': 64,
        'chassis': 64,
        'contact': 65535,
        'contract_number': 64,
        'date_hw_decomm': 64,
        'date_hw_expiry': 64,
        'date_hw_install': 64,
        'date_hw_purchase': 64,
        'deployment_status': 64,
        'hardware': 255,
        'hardware_full': 65535,
        'host_netmask': 39,
        'host_networks': 65535,
        'host_router': 39,
        'hw_arch': 32,
        'installer_name': 64,
        'location': 65535,
        'location_lat': 16,
        'location_lon': 16,
        'macaddress_a': 64,
        'macaddress_b': 64,
        'model_field': 64,
        'name': 128,
        'notes': 65535,
        'oob_ip': 39,
        'oob_netmask': 39,
        'oob_router': 39,
        'os': 128,
        'os_full': 255,
        'os_short': 128,
        'poc_1_cell': 64,
        'poc_1_email': 128,
        'poc_1_name': 128,
        'poc_1_notes': 65535,
        'poc_1_phone_a': 64,
        'poc_1_phone_b': 64,
        'poc_1_screen': 64,
        'poc_2_cell': 64,
        'poc_2_email': 128,
        'poc_2_name': 128,
        'poc_2_notes': 65535,
        'poc_2_phone_a': 64,
        'poc_2_phone_b': 64,
        'poc_2_screen': 64,
        'serialno_a': 64,
        'serialno_b': 64,
        'site_address_a': 128,
        'site_address_b': 128,
        'site_address_c': 128,
        'site_city': 128,
        'site_country': 64,
        'site_notes': 65535,
        'site_rack': 128,
        'site_state': 64,
        'site_zip': 64,
        'software': 255,
        'software_app_a': 64,
        'software_app_b': 64,
        'software_app_c': 64,
        'software_app_d': 64,
        'software_app_e': 64,
        'software_full': 65535,
        'tag': 64,
        'type': 64,
        'type_full': 64,
        'url_a': 2048,
        'url_b': 2048,
        'url_c': 2048,
        'vendor': 64,
    }
