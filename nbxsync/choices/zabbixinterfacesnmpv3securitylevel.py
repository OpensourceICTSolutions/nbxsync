from django.db import models

__all__ = ('ZabbixInterfaceSNMPV3SecurityLevelChoices',)


class ZabbixInterfaceSNMPV3SecurityLevelChoices(models.IntegerChoices):
    NOAUTHNOPRIV = 0, 'noAuthNoPriv'
    AUTHNOPRIV = 1, 'authNoPriv'
    AUTHPRIV = 2, 'authPriv'
