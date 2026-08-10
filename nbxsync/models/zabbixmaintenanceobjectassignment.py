from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db import models

from netbox.models import NetBoxModel

from nbxsync.constants.assignment_models import MAINTENANCE_ASSIGNMENT_OBJECTS
from nbxsync.models import ZabbixHostgroup

__all__ = ('ZabbixMaintenanceObjectAssignment',)


class ZabbixMaintenanceObjectAssignment(NetBoxModel):
    zabbixmaintenance = models.ForeignKey('nbxsync.ZabbixMaintenance', on_delete=models.CASCADE, related_name='zabbixmaintenanceobjectassignment')
    assigned_object_type = models.ForeignKey(to=ContentType, limit_choices_to=MAINTENANCE_ASSIGNMENT_OBJECTS, on_delete=models.CASCADE, related_name='+', blank=True, null=True)
    assigned_object_id = models.PositiveBigIntegerField(blank=True, null=True)
    assigned_object = GenericForeignKey(ct_field='assigned_object_type', fk_field='assigned_object_id')

    class Meta:
        verbose_name = 'Zabbix Maintenance Object Assignment'
        verbose_name_plural = 'Zabbix Maintenance Object Assignments'
        ordering = ('-created',)

        constraints = [
            models.UniqueConstraint(
                fields=['zabbixmaintenance', 'assigned_object_type', 'assigned_object_id'],
                name='%(app_label)s_%(class)s_unique__maintenanceobjectassignment_per_object',
                violation_error_message='Object can only be assigned once to a Zabbix Maintenance object',
            )
        ]

    def clean(self):
        super().clean()

        if self.assigned_object_type is None or self.assigned_object_id is None:
            # Nothing to check yet; let the FK/id validators handle emptiness.
            return

        if isinstance(self.assigned_object, ZabbixHostgroup) and self.assigned_object.is_template():
            raise ValidationError({'assigned_object_id': _('A templated Zabbix Hostgroup cannot be assigned to a maintenance window.')})

    def __str__(self):
        return f'{self.assigned_object} ({self.zabbixmaintenance})'
