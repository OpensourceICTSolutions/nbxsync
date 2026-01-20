import re

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from netbox.models import NetBoxModel
from ipam.models import IPAddress

from nbxsync.choices import (
    IPMIAuthTypeChoices,
    IPMIPrivilegeChoices,
    ZabbixHostInterfaceSNMPVersionChoices,
    ZabbixHostInterfaceTypeChoices,
    ZabbixInterfaceSNMPV3AuthProtoChoices,
    ZabbixInterfaceSNMPV3PrivProtoChoices,
    ZabbixInterfaceSNMPV3SecurityLevelChoices,
    ZabbixInterfaceTypeChoices,
    ZabbixInterfaceUseChoices,
    ZabbixTLSChoices,
)

from nbxsync.constants import DEVICE_OR_VM_ASSIGNMENT_MODELS, CONFIGGROUP_OBJECTS
from nbxsync.models import SyncInfoModel, ZabbixConfigurationGroup


def default_tls_accept():
    return [ZabbixTLSChoices.NO_ENCRYPTION]


class ZabbixHostInterface(SyncInfoModel, NetBoxModel):
    zabbixserver = models.ForeignKey(to='nbxsync.ZabbixServer', on_delete=models.CASCADE, verbose_name=_('Zabbix Server'))
    zabbixconfigurationgroup = models.ForeignKey('nbxsync.ZabbixConfigurationGroup', on_delete=models.SET_NULL, blank=True, null=True, related_name='zabbixconfigurationgroup')

    type = models.IntegerField(choices=ZabbixHostInterfaceTypeChoices, default=ZabbixHostInterfaceTypeChoices.AGENT, verbose_name=_('Host interface type'))
    interfaceid = models.IntegerField(blank=True, null=True)
    useip = models.IntegerField(choices=ZabbixInterfaceUseChoices, default=ZabbixInterfaceUseChoices.IP, verbose_name=_('Connect via'))
    interface_type = models.IntegerField(choices=ZabbixInterfaceTypeChoices, default=ZabbixInterfaceTypeChoices.DEFAULT, verbose_name=_('Interface type'))
    dns = models.CharField(max_length=255, blank=True, verbose_name=_('DNS Name'))
    ip = models.ForeignKey(to=IPAddress, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('IP Address'), related_name='zabbix_hostinterfaces')
    port = models.IntegerField(blank=False, null=False, verbose_name=_('Port number'))

    assigned_object_type = models.ForeignKey(to=ContentType, limit_choices_to=(DEVICE_OR_VM_ASSIGNMENT_MODELS | CONFIGGROUP_OBJECTS), on_delete=models.CASCADE, related_name='+', blank=True, null=True)
    assigned_object_id = models.PositiveBigIntegerField(blank=True, null=True)
    assigned_object = GenericForeignKey(ct_field='assigned_object_type', fk_field='assigned_object_id')

    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.SET_NULL)

    # Agent-specific fields
    tls_connect = models.PositiveSmallIntegerField(choices=ZabbixTLSChoices, default=ZabbixTLSChoices.NO_ENCRYPTION, blank=True, null=True)
    tls_accept = ArrayField(base_field=models.PositiveSmallIntegerField(choices=ZabbixTLSChoices), default=default_tls_accept, blank=True)
    tls_issuer = models.CharField(max_length=255, blank=True)
    tls_subject = models.CharField(max_length=255, blank=True)
    tls_psk_identity = models.CharField(max_length=255, blank=True)
    tls_psk = models.CharField(max_length=1024, blank=True)

    # SNMP (v1/v2/v3)
    snmp_version = models.IntegerField(choices=ZabbixHostInterfaceSNMPVersionChoices, default=ZabbixHostInterfaceSNMPVersionChoices.SNMPV2, blank=True, null=True, verbose_name=_('SNMP Version'))
    snmp_usebulk = models.BooleanField(default=True, verbose_name=_('SNMP Combined requests'))

    # SNMPv1/2-specific fields
    snmp_community = models.CharField(max_length=75, blank=True, verbose_name=_('SNMPv1/2 Community'))
    snmp_pushcommunity = models.BooleanField(default=True)

    # SNMPv3-specific fields
    snmpv3_context_name = models.CharField(max_length=50, blank=True, verbose_name=_('Context Name'))
    snmpv3_security_name = models.CharField(max_length=50, blank=True, verbose_name=_('Security Name'))
    snmpv3_security_level = models.IntegerField(choices=ZabbixInterfaceSNMPV3SecurityLevelChoices, default=ZabbixInterfaceSNMPV3SecurityLevelChoices.NOAUTHNOPRIV, blank=True, null=True, verbose_name=_('Security Level'))
    snmpv3_authentication_passphrase = models.CharField(max_length=50, blank=True, verbose_name=_('Authentication passphrase'))
    snmpv3_authentication_protocol = models.IntegerField(choices=ZabbixInterfaceSNMPV3AuthProtoChoices, default=ZabbixInterfaceSNMPV3AuthProtoChoices.MD5, blank=True, null=True, verbose_name=_('Authentication protocol'))
    snmpv3_privacy_passphrase = models.CharField(max_length=50, blank=True, verbose_name=_('Privacy passphrase'))
    snmpv3_privacy_protocol = models.IntegerField(choices=ZabbixInterfaceSNMPV3PrivProtoChoices, default=ZabbixInterfaceSNMPV3PrivProtoChoices.DES, blank=True, null=True, verbose_name=_('Privacy protocol'))

    # IPMI
    ipmi_authtype = models.IntegerField(choices=IPMIAuthTypeChoices, default=IPMIAuthTypeChoices.DEFAULT, blank=True, null=True, verbose_name=_('Auth type'))
    ipmi_password = models.CharField(max_length=255, blank=True, verbose_name=_('Password'))
    ipmi_privilege = models.IntegerField(choices=IPMIPrivilegeChoices, default=IPMIPrivilegeChoices.USER, blank=True, null=True, verbose_name=_('Privilege'))
    ipmi_username = models.CharField(max_length=50, blank=True, verbose_name=_('Username'))

    prerequisite_models = ('nbxsync.ZabbixServer',)

    def __str__(self):
        return f'Hostinterface {self.get_type_display()} on {self.zabbixserver} ({self.assigned_object or "Unassigned"})'

    class Meta:
        verbose_name = 'Zabbix Host Interface'
        verbose_name_plural = 'Zabbix Host Interfaces'
        ordering = ('-created',)
        constraints = [
            # Only ONE default interface per (server, type, assigned object)
            models.UniqueConstraint(
                fields=['zabbixserver', 'type', 'assigned_object_type', 'assigned_object_id'],
                condition=Q(interface_type=ZabbixInterfaceTypeChoices.DEFAULT),
                name='%(app_label)s_%(class)s_unique_default__server_type_object',
                violation_error_message='A default Hostinterface of this type has already been defined for this object.',
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}

        if self.assigned_object_type is None or self.assigned_object_id is None:
            raise ValidationError('An assigned object must be provided')

        if self.zabbixserver_id is None:
            errors['zabbixserver'] = _('A hostinterface must always be assigned to a Zabbix Server')

        # Validate TLS PSK requirement
        if self.tls_connect == ZabbixTLSChoices.PSK or ZabbixTLSChoices.PSK in self.tls_accept:
            if len(self.tls_psk) < 32:
                errors['tls_psk'] = _('TLS PSK must be at least 32 characters long.')
            elif not re.fullmatch(r'[0-9a-fA-F]+', self.tls_psk):
                errors['tls_psk'] = _('TLS PSK must contain only hexadecimal characters (0-9, a-f, A-F).')

            if self.tls_psk_identity == '':
                errors['tls_psk_identity'] = _('TLS PSK Identity must be provided when using PSK encryption.')

        # Example: require SNMPv3 fields
        if self.type == ZabbixHostInterfaceTypeChoices.SNMP and self.snmp_version == ZabbixHostInterfaceSNMPVersionChoices.SNMPV3:
            if not self.snmpv3_security_name:
                errors['snmpv3_security_name'] = _('Required for SNMPv3 interface.')

            if self.snmpv3_authentication_passphrase and len(self.snmpv3_authentication_passphrase) < 8:
                errors['snmpv3_authentication_passphrase'] = _('Authentication passphrase must be at least 8 characters long.')

            if self.snmpv3_privacy_passphrase and len(self.snmpv3_privacy_passphrase) < 8:
                errors['snmpv3_privacy_passphrase'] = _('Privacy passphrase must be at least 8 characters long.')

        # If the assigned object type is *not* a ZabbixConfigurationGroup, we validate the IP and/or DNS entry
        if self.assigned_object_type != ContentType.objects.get_for_model(ZabbixConfigurationGroup):
            # Validate based on connection method
            if self.useip == ZabbixInterfaceUseChoices.IP:
                if not self.ip:
                    errors['ip'] = _('An IP address is required when "Connect via" is set to IP.')

            if self.useip == ZabbixInterfaceUseChoices.DNS:
                if not self.dns:
                    errors['dns'] = _('A DNS name is required when "Connect via" is set to DNS.')

        # # If ZbxConfigGroup, ensure neither IP and DNS are set, as we cannot support this
        # # The IP will be set upon assignment!
        if self.assigned_object_type == ContentType.objects.get_for_model(ZabbixConfigurationGroup):
            self.ip = None
            self.dns = ''

        if errors:
            raise ValidationError(errors)

    def get_useip_display(self):
        return ZabbixInterfaceUseChoices(self.useip).label

    def get_type_display(self):
        return ZabbixHostInterfaceTypeChoices(self.type).label

    def get_tls_connect_display(self):
        return ZabbixTLSChoices(self.tls_connect).label

    def get_tls_accept_display(self):
        return [ZabbixTLSChoices(value).label for value in self.tls_accept if value in ZabbixTLSChoices.values]

    def get_ipmi_privlege_display(self):
        return IPMIPrivilegeChoices(self.ipmi_privilege).label

    def get_ipmi_authtype_display(self):
        return IPMIAuthTypeChoices(self.ipmi_authtype).label

    def get_snmp_version_display(self):
        return ZabbixHostInterfaceSNMPVersionChoices(self.snmp_version).label

    def get_snmpv3_security_level_display(self):
        return ZabbixInterfaceSNMPV3SecurityLevelChoices(self.snmpv3_security_level).label

    def get_snmpv3_authentication_protocol_display(self):
        return ZabbixInterfaceSNMPV3AuthProtoChoices(self.snmpv3_authentication_protocol).label

    def get_snmpv3_snmpv3_privacy_protocol_display(self):
        return ZabbixInterfaceSNMPV3PrivProtoChoices(self.snmpv3_privacy_protocol).label
