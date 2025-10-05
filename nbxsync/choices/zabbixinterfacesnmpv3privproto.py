from django.db import models

__all__ = ('ZabbixInterfaceSNMPV3PrivProtoChoices',)


class ZabbixInterfaceSNMPV3PrivProtoChoices(models.IntegerChoices):
    DES = 0, 'DES'
    AES128 = 1, 'AES128'
    AES192 = 2, 'AES192'
    AES256 = 3, 'AES256'
    AES192C = 4, 'AES192C'
    AES256C = 5, 'AES256C'
