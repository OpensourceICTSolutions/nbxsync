from django.db import models

__all__ = ('IPMIAuthTypeChoices',)


class IPMIAuthTypeChoices(models.IntegerChoices):
    DEFAULT = -1, 'Default'
    NONE = 0, 'None'
    MD2 = 1, 'MD2'
    MD5 = 2, 'MD5'
    STRAIGHT = 4, 'Straight'
    OEM = 5, 'OEM'
    RMCP_PLUS = 6, 'RMCP+'
