from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models

from netbox.models import NetBoxModel

from nbxsync.constants import ASSIGNMENT_MODELS

__all__ = ('ZabbixTemplateAssignment',)


class ZabbixTemplateAssignment(NetBoxModel):
    zabbixtemplate = models.ForeignKey(to='nbxsync.ZabbixTemplate', on_delete=models.CASCADE, related_name='zabbixtemplateassignment')
    assigned_object_type = models.ForeignKey(to=ContentType, limit_choices_to=ASSIGNMENT_MODELS, on_delete=models.CASCADE, related_name='+', blank=True, null=True)
    assigned_object_id = models.PositiveBigIntegerField(blank=True, null=True)
    assigned_object = GenericForeignKey(ct_field='assigned_object_type', fk_field='assigned_object_id')
    zabbixconfigurationgroup = models.ForeignKey('nbxsync.ZabbixConfigurationGroup', on_delete=models.SET_NULL, blank=True, null=True)

    prerequisite_models = ('nbxsync.ZabbixTemplate',)

    class Meta:
        verbose_name = 'Zabbix Template Assignment'
        verbose_name_plural = 'Zabbix Template Assignments'
        ordering = ('-created',)

        constraints = [
            models.UniqueConstraint(
                fields=['zabbixtemplate', 'assigned_object_type', 'assigned_object_id'],
                name='%(app_label)s_%(class)s_unique__templateassignment_per_object',
                violation_error_message='Template can only be assigned once to a given object',
            )
        ]

    def clean(self):
        if self.assigned_object_type is None or self.assigned_object_id is None:
            raise ValidationError('An assigned object must be provided')
        super().clean()

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        ret_val = ''
        if self.assigned_object:
            ret_val = f'{str(self.assigned_object)} - {str(self.zabbixtemplate)}'

        return ret_val
