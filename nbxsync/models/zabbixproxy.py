import ipaddress
import re

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext as _

from netbox.models import NetBoxModel

from nbxsync.choices import *
from nbxsync.models import SyncInfoModel
from nbxsync.validators import validate_address

__all__ = ('ZabbixProxy',)


def default_tls_accept():
    return [ZabbixTLSChoices.NO_ENCRYPTION]


class ZabbixProxy(SyncInfoModel, NetBoxModel):
    zabbixserver = models.ForeignKey('nbxsync.ZabbixServer', on_delete=models.CASCADE, related_name='zabbixproxies')
    proxygroup = models.ForeignKey('nbxsync.ZabbixProxyGroup', on_delete=models.SET_NULL, related_name='zabbixproxies', null=True, blank=True)
    proxyid = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=255)
    local_address = models.CharField(max_length=255, blank=True)
    local_port = models.PositiveIntegerField(default=10051, blank=True, validators=[MinValueValidator(0), MaxValueValidator(65535)], help_text='Enter a valid IP port number (0-65535)')
    operating_mode = models.PositiveSmallIntegerField(choices=ZabbixProxyTypeChoices, default=ZabbixProxyTypeChoices.ACTIVE)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    port = models.CharField(max_length=10, default='10051', blank=True)
    allowed_addresses = ArrayField(base_field=models.GenericIPAddressField(), blank=True, default=list, help_text='List of allowed IP addresses')
    tls_connect = models.PositiveSmallIntegerField(choices=ZabbixTLSChoices, default=ZabbixTLSChoices.NO_ENCRYPTION)
    tls_accept = ArrayField(base_field=models.PositiveSmallIntegerField(choices=ZabbixTLSChoices), default=default_tls_accept, blank=True)
    tls_issuer = models.CharField(max_length=255, blank=True)
    tls_subject = models.CharField(max_length=255, blank=True)
    tls_psk_identity = models.CharField(max_length=255, blank=True)
    tls_psk = models.CharField(max_length=255, blank=True)  # write-only
    custom_timeouts = models.BooleanField(default=False)
    timeout_zabbix_agent = models.CharField(max_length=20, blank=True)
    timeout_simple_check = models.CharField(max_length=20, blank=True)
    timeout_snmp_agent = models.CharField(max_length=20, blank=True)
    timeout_external_check = models.CharField(max_length=20, blank=True)
    timeout_db_monitor = models.CharField(max_length=20, blank=True)
    timeout_http_agent = models.CharField(max_length=20, blank=True)
    timeout_ssh_agent = models.CharField(max_length=20, blank=True)
    timeout_telnet_agent = models.CharField(max_length=20, blank=True)
    timeout_script = models.CharField(max_length=20, blank=True)
    timeout_browser = models.CharField(max_length=20, blank=True)

    prerequisite_models = ('nbxsync.ZabbixServer',)

    class Meta:
        verbose_name = 'Zabbix Proxy'
        verbose_name_plural = 'Zabbix Proxies'
        ordering = ('-created',)

    def clean(self):
        super().clean()
        errors = {}

        # Validate local_address field
        if not self.local_address and self.proxygroup is not None and self.operating_mode == ZabbixProxyTypeChoices.ACTIVE:
            errors['local_address'] = _('Local Address must be specified when part of a ProxyGroup and Operating Mode is set to Active')

        # Validate if local_address is valid
        if self.local_address is not None and self.operating_mode == ZabbixProxyTypeChoices.ACTIVE:
            try:
                if self.local_address != '':
                    validate_address(self.local_address)
            except ValidationError as e:
                errors['local_address'] = _(str(e))

        # Validate address field
        if self.address is None and self.operating_mode == ZabbixProxyTypeChoices.PASSIVE:
            errors['address'] = _('Address must be specified when Operating Mode is set to Passive')

        # Validate if address is valid
        if self.address is not None and self.operating_mode == ZabbixProxyTypeChoices.PASSIVE:
            try:
                validate_address(self.address)
            except ValidationError as e:
                errors['address'] = _(str(e))

        # Validate allowed_addresses
        if self.allowed_addresses:
            seen = set()
            normalized = ''
            for ip in self.allowed_addresses:
                try:
                    normalized = str(ipaddress.ip_address(ip.strip()))
                except ValueError:
                    errors['allowed_addresses'] = f"'{ip}' is not a valid IP address."

                if normalized in seen:
                    errors['allowed_addresses'] = f'Duplicate IP address found: {normalized}'
                seen.add(normalized)

        # Validate TLS PSK requirement
        if self.tls_connect == ZabbixTLSChoices.PSK or ZabbixTLSChoices.PSK in self.tls_accept:
            if len(self.tls_psk) < 32:
                errors['tls_psk'] = _('TLS PSK must be at least 32 characters long.')
            elif not re.fullmatch(r'[0-9a-fA-F]+', self.tls_psk):
                errors['tls_psk'] = _('TLS PSK must contain only hexadecimal characters (0-9, a-f, A-F).')

            if self.tls_psk_identity == '':
                errors['tls_psk_identity'] = _('TLS PSK Identity must be provided when using PSK encryption.')

        # Validate timeout fields if custom_timeouts is enabled
        if self.custom_timeouts:
            timeout_fields = [
                'timeout_zabbix_agent',
                'timeout_simple_check',
                'timeout_snmp_agent',
                'timeout_external_check',
                'timeout_db_monitor',
                'timeout_http_agent',
                'timeout_ssh_agent',
                'timeout_telnet_agent',
                'timeout_script',
                'timeout_browser',
            ]
            for field in timeout_fields:
                value = getattr(self, field)
                if not value:
                    errors[field] = _(f'{field.replace("_", " ").capitalize()} is required when custom timeouts are enabled.')
                else:
                    # Validate failover_delay format and bounds (10s–15m)

                    match = re.fullmatch(r'(\d+)([sm])', value)
                    if not match:
                        errors[field] = "Invalid format: use integer + 's' or 'm', e.g. '90s', '5m'."
                    else:
                        val, unit = int(match.group(1)), match.group(2)
                        seconds = val * (60 if unit == 'm' else 1)
                        if seconds < 1 or seconds > 600:
                            errors[field] = 'Value must be between 1s and 10m.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        # Just clear the fields that should be cleared based on the final state

        if self.operating_mode == ZabbixProxyTypeChoices.ACTIVE:
            self.address = ''
            self.port = ''
            self.tls_connect = ZabbixTLSChoices.NO_ENCRYPTION

        if self.operating_mode == ZabbixProxyTypeChoices.PASSIVE:
            self.local_address = ''
            self.local_port = 10051
            self.allowed_addresses = []
            self.tls_accept = [ZabbixTLSChoices.NO_ENCRYPTION]

            if self.tls_connect == ZabbixTLSChoices.NO_ENCRYPTION:
                self.tls_issuer = ''
                self.tls_subject = ''
                self.tls_psk_identity = ''
                self.tls_psk = ''

            if self.tls_connect == ZabbixTLSChoices.PSK:
                self.tls_issuer = ''
                self.tls_subject = ''

            if self.tls_connect == ZabbixTLSChoices.CERT:
                self.tls_psk_identity = ''
                self.tls_psk = ''

        if self.custom_timeouts == 0:
            self.timeout_zabbix_agent = ''
            self.timeout_simple_check = ''
            self.timeout_snmp_agent = ''
            self.timeout_external_check = ''
            self.timeout_db_monitor = ''
            self.timeout_http_agent = ''
            self.timeout_ssh_agent = ''
            self.timeout_telnet_agent = ''
            self.timeout_script = ''
            self.timeout_browser = ''

        super().save(*args, **kwargs)

    def get_tls_accept_display(self):
        return [ZabbixTLSChoices(value).label for value in self.tls_accept if value in ZabbixTLSChoices.values]

    def get_operating_mode_display(self):
        return ZabbixProxyTypeChoices(self.operating_mode).label

    def __str__(self):
        return f'{self.name} ({self.get_operating_mode_display()})'
