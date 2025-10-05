from django.db import models

__all__ = ('ZabbixHostInterfaceTypeChoices',)


class ZabbixHostInterfaceTypeChoices(models.IntegerChoices):
    AGENT = 1, 'Agent'
    SNMP = 2, 'SNMP'
    IPMI = 3, 'IPMI'
    JMX = 4, 'JMX'
