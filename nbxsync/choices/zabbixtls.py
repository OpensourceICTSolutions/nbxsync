from django.db import models

__all__ = ('ZabbixTLSChoices',)


class ZabbixTLSChoices(models.IntegerChoices):
    NO_ENCRYPTION = 1, 'No Encryption'
    PSK = 2, 'Pre-Shared key'
    CERT = 4, 'Certificate'
