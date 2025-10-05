from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models

from netbox.models import NetBoxModel

from nbxsync.choices import ZabbixMacroTypeChoices
from nbxsync.constants import MACRO_ASSIGNMENT_MODELS

__all__ = ('ZabbixMacro',)


class ZabbixMacro(NetBoxModel):
    macro = models.CharField(max_length=512, blank=False)
    value = models.CharField(max_length=512, blank=True)
    description = models.CharField(max_length=1024, blank=True)
    hostmacroid = models.IntegerField(blank=True, null=True)
    type = models.CharField(max_length=2, choices=ZabbixMacroTypeChoices.choices)
    assigned_object_type = models.ForeignKey(to=ContentType, limit_choices_to=MACRO_ASSIGNMENT_MODELS, on_delete=models.CASCADE, related_name='+', blank=True, null=True)
    assigned_object_id = models.PositiveBigIntegerField(blank=True, null=True)
    assigned_object = GenericForeignKey(ct_field='assigned_object_type', fk_field='assigned_object_id')

    class Meta:
        verbose_name = 'Zabbix Macro'
        verbose_name_plural = 'Zabbix Macros'
        ordering = ('-created',)

        constraints = [
            models.UniqueConstraint(
                fields=['macro', 'assigned_object_type', 'assigned_object_id'],
                name='%(app_label)s_%(class)s_unique__macro_per_assigned_object',
                violation_error_message='Macro must be unique per Assigned Object',
            ),
            models.UniqueConstraint(
                fields=['hostmacroid', 'assigned_object_type', 'assigned_object_id'],
                name='%(app_label)s_%(class)s_unique__hostmacroid_per_assigned_object',
                violation_error_message='Host Macro ID must be unique per Assigned Object',
            ),
        ]

    def clean(self):
        super().clean()
        if self.assigned_object_type is None or self.assigned_object_id is None:
            raise ValidationError('An assigned object must be provided')

    def save(self, *args, **kwargs):
        # Ensure macro starts with '{$' and ends with '}'
        if self.macro:
            trimmed = self.macro.strip()
            if not trimmed.startswith('{$'):
                trimmed = '{$' + trimmed.lstrip('{').lstrip('$')
            if not trimmed.endswith('}'):
                trimmed = trimmed.rstrip('}') + '}'
            self.macro = trimmed

        super().save(*args, **kwargs)

    def __str__(self):
        if self.assigned_object:
            return f'{self.macro} ({self.assigned_object.name})'

        return self.macro
