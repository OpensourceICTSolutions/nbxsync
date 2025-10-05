from django.db import models

__all__ = ('HostInterfaceRequirementChoices',)


class HostInterfaceRequirementChoices(models.IntegerChoices):
    NONE = 0, 'None'  # No interface required
    ANY = -1, 'Any'  # Any interface required
    AGENT = 1, 'Agent'
    SNMP = 2, 'SNMP'
    IPMI = 3, 'IPMI'
    JMX = 4, 'JMX'
