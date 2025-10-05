from django.db import models

__all__ = ('ZabbixMaintenanceTagsEvalChoices',)


class ZabbixMaintenanceTagsEvalChoices(models.IntegerChoices):
    AND_OR = 0, 'And/Or'
    OR = 2, 'Or'
