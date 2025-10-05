from django.db import models

__all__ = ('ZabbixMacroTypeChoices',)


class ZabbixMacroTypeChoices(models.TextChoices):
    TEXT = '0', 'Text macro'
    SECRET = '1', 'Secret macro'
    VAULT = '2', 'Vault secret'
