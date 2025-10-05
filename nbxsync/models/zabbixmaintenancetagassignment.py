from django.core.exceptions import ValidationError
from django.db import models

from netbox.models import NetBoxModel

from nbxsync.choices import ZabbixMaintenanceTagOperatorChoices


__all__ = ('ZabbixMaintenanceTagAssignment',)


class ZabbixMaintenanceTagAssignment(NetBoxModel):
    zabbixmaintenance = models.ForeignKey('nbxsync.ZabbixMaintenance', on_delete=models.CASCADE, related_name='zabbixmaintenancetagassignment')
    zabbixtag = models.ForeignKey('nbxsync.ZabbixTag', on_delete=models.CASCADE, related_name='zabbixmaintenancetagassignment')
    operator = models.PositiveSmallIntegerField(choices=ZabbixMaintenanceTagOperatorChoices, default=ZabbixMaintenanceTagOperatorChoices.CONTAINS)
    value = models.CharField(max_length=512, blank=False)

    class Meta:
        verbose_name = 'Zabbix Maintenance Tag Assignment'
        verbose_name_plural = 'Zabbix Maintenance Tag Assignments'
        ordering = ('-created',)

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'zabbixmaintenance',
                    'zabbixtag',
                ],
                name='%(app_label)s_%(class)s_unique__maintenancetagassignment_per_object',
                violation_error_message='Tags can only be assigned once to a Zabbix Maintenance',
            )
        ]

    def clean(self):
        super().clean()

        if self.zabbixtag.is_template():
            raise ValidationError('No templated tag is allowed!')

    def __str__(self):
        return f'{self.zabbixtag} ({self.zabbixmaintenance})'
