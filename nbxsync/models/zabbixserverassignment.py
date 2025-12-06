from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models

from netbox.models import NetBoxModel

from nbxsync.constants import ASSIGNMENT_MODELS
from nbxsync.models import SyncInfoModel

__all__ = ('ZabbixServerAssignment',)


class ZabbixServerAssignment(SyncInfoModel, NetBoxModel):
    zabbixserver = models.ForeignKey('nbxsync.ZabbixServer', on_delete=models.CASCADE, related_name='zabbixserverassignment')
    hostid = models.IntegerField(blank=True, null=True)
    zabbixproxy = models.ForeignKey(to='nbxsync.ZabbixProxy', blank=True, null=True, on_delete=models.CASCADE)
    zabbixproxygroup = models.ForeignKey(to='nbxsync.ZabbixProxyGroup', blank=True, null=True, on_delete=models.CASCADE)
    assigned_object_type = models.ForeignKey(to=ContentType, limit_choices_to=ASSIGNMENT_MODELS, on_delete=models.CASCADE, related_name='+', blank=True, null=True)
    assigned_object_id = models.PositiveBigIntegerField(blank=True, null=True)
    assigned_object = GenericForeignKey(ct_field='assigned_object_type', fk_field='assigned_object_id')
    zabbixconfigurationgroup = models.ForeignKey('nbxsync.ZabbixConfigurationGroup', on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        verbose_name = 'Zabbix Server Assignment'
        verbose_name_plural = 'Zabbix Server Assignments'
        ordering = ('-created',)

        constraints = [
            models.UniqueConstraint(
                fields=['zabbixserver', 'assigned_object_type', 'assigned_object_id'],
                name='%(app_label)s_%(class)s_unique__zabbixserverassignment_per_object',
                violation_error_message='A Zabbix server can only be assigned once to a given object',
            )
        ]

    def clean(self):
        if self.assigned_object_type is None or self.assigned_object_id is None:
            raise ValidationError('An assigned object must be provided')

        if self.zabbixproxy is not None and self.zabbixproxygroup is not None:
            raise ValidationError('You cannot set both a proxy and proxygroup')
        super().clean()

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        ret_val = ''
        if self.assigned_object:
            ret_val = f'{str(self.assigned_object)} - {str(self.zabbixserver)} '

        return ret_val
