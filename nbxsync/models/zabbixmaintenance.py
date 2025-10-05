from django.db import models

from netbox.models import NetBoxModel

from nbxsync.choices import ZabbixMaintenanceTagsEvalChoices, ZabbixMaintenanceTypeChoices
from nbxsync.models import SyncInfoModel

__all__ = ('ZabbixMaintenance',)


class ZabbixMaintenance(SyncInfoModel, NetBoxModel):
    zabbixserver = models.ForeignKey(to='nbxsync.ZabbixServer', on_delete=models.CASCADE)

    maintenanceid = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=512, blank=False)
    active_since = models.DateTimeField(blank=False)
    active_till = models.DateTimeField(blank=False)
    description = models.CharField(max_length=512, blank=True)
    maintenance_type = models.PositiveSmallIntegerField(choices=ZabbixMaintenanceTypeChoices, default=ZabbixMaintenanceTypeChoices.WITH_COLLECTION)
    tags_evaltype = models.PositiveSmallIntegerField(choices=ZabbixMaintenanceTagsEvalChoices, default=ZabbixMaintenanceTagsEvalChoices.AND_OR)
    automatic = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Zabbix Maintenance window'
        verbose_name_plural = 'Zabbix Maintenance windows'
        ordering = ('-created',)

        constraints = [
            models.UniqueConstraint(
                fields=['name', 'zabbixserver'],
                name='%(app_label)s_%(class)s_unique__maintenance_per_zabbixserver',
                violation_error_message='Maintenance name must be unique per Zabbix Server',
            ),
            models.UniqueConstraint(
                fields=['maintenanceid', 'zabbixserver'],
                name='%(app_label)s_%(class)s_unique__maintenanceid_per_zabbixserver',
                violation_error_message='Maintenance ID must be unique per Zabbix Server',
            ),
        ]

    def get_maintenance_type_display(self):
        return ZabbixMaintenanceTypeChoices(self.maintenance_type).label

    def get_tags_evaltype_display(self):
        return ZabbixMaintenanceTagsEvalChoices(self.tags_evaltype).label

    def __str__(self):
        return f'{self.name} ({self.zabbixserver.name})'
