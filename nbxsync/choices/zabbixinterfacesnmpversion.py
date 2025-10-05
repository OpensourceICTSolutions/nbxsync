from django.db import models

__all__ = ('ZabbixHostInterfaceSNMPVersionChoices',)


class ZabbixHostInterfaceSNMPVersionChoices(models.IntegerChoices):
    SNMPV1 = 1, 'SNMPv1'
    SNMPV2 = 2, 'SNMPv2'
    SNMPV3 = 3, 'SNMPv3'
