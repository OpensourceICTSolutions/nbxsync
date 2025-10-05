from django.db import models

__all__ = ('IPMIPrivilegeChoices',)


class IPMIPrivilegeChoices(models.IntegerChoices):
    CALLBACK = 1, 'Callback'
    USER = 2, 'User'
    OPERATOR = 3, 'Operator'
    ADMIN = 4, 'Admin'
    OEM = 5, 'Oem'
