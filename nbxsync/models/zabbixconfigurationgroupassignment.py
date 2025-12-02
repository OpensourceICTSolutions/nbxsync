from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from netbox.models import NetBoxModel

from nbxsync.constants import DEVICE_OR_VM_ASSIGNMENT_MODELS

__all__ = ('ZabbixConfigurationGroupAssignment',)


class ZabbixConfigurationGroupAssignment(NetBoxModel):
    zabbixconfigurationgroup = models.ForeignKey('nbxsync.ZabbixConfigurationGroup', on_delete=models.CASCADE, related_name='zabbixconfigurationgroupassignment')

    assigned_object_type = models.ForeignKey(to=ContentType, limit_choices_to=DEVICE_OR_VM_ASSIGNMENT_MODELS, on_delete=models.CASCADE, related_name='+', blank=True, null=True)
    assigned_object_id = models.PositiveBigIntegerField(blank=True, null=True)
    assigned_object = GenericForeignKey(ct_field='assigned_object_type', fk_field='assigned_object_id')

    class Meta:
        verbose_name = 'Zabbix Configuration Group Assignment'
        verbose_name_plural = 'Zabbix Configuration Group Assignments'
        ordering = ('-created',)

        constraints = [
            models.UniqueConstraint(
                fields=['zabbixconfigurationgroup', 'assigned_object_type', 'assigned_object_id'],
                name='%(app_label)s_%(class)s_unique__zabbixconfigurationgroupassignment_per_object',
                violation_error_message='Object can only be assigned once to a Zabbix Configuration Group',
            )
        ]

    def __str__(self):
        return self.zabbixconfigurationgroup.name
