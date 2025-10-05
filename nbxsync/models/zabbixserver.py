from django.db import models

from netbox.models import NetBoxModel

from nbxsync.models import SyncInfoModel


__all__ = ('ZabbixServer',)


class ZabbixServer(SyncInfoModel, NetBoxModel):
    name = models.CharField(blank=False)
    description = models.CharField(blank=True)
    url = models.URLField(blank=False)
    token = models.CharField(blank=False)
    validate_certs = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Zabbix Server'
        verbose_name_plural = 'Zabbix Servers'
        ordering = ('-created',)

        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                name='%(app_label)s_%(class)s_unique__name',
                violation_error_message='The Zabbix Server name must be unique',
            ),
            models.UniqueConstraint(
                fields=['url'],
                name='%(app_label)s_%(class)s_unique__url',
                violation_error_message='The Zabbix Server URL must be unique',
            ),
        ]

    def __str__(self):
        return self.name
