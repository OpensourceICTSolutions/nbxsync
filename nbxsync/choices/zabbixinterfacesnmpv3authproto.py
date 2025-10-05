from django.db import models

__all__ = ('ZabbixInterfaceSNMPV3AuthProtoChoices',)


class ZabbixInterfaceSNMPV3AuthProtoChoices(models.IntegerChoices):
    MD5 = 0, 'MD5'
    SHA1 = 1, 'SHA1'
    SHA224 = 2, 'SHA224'
    SHA256 = 3, 'SHA256'
    SHA384 = 4, 'SHA384'
    SHA512 = 5, 'SHA512'
