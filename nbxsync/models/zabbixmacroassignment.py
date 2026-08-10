import re

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models

from jinja2 import TemplateError, TemplateSyntaxError, UndefinedError
from utilities.jinja2 import render_jinja2

from netbox.models import NetBoxModel
from nbxsync.constants.assignment_models import ASSIGNMENT_MODELS
from nbxsync.constants.template_pattern import TEMPLATE_PATTERN
from nbxsync.models import SyncInfoModel, ZabbixConfigurationGroup

__all__ = ('ZabbixMacroAssignment',)


class ZabbixMacroAssignment(SyncInfoModel, NetBoxModel):
    zabbixmacro = models.ForeignKey('nbxsync.ZabbixMacro', on_delete=models.CASCADE, related_name='zabbixmacroassignment')
    is_regex = models.BooleanField(default=False)
    context = models.CharField(max_length=128, blank=True)
    value = models.CharField(max_length=2048, blank=False)
    macroid = models.IntegerField(blank=True, null=True)
    assigned_object_type = models.ForeignKey(to=ContentType, limit_choices_to=ASSIGNMENT_MODELS, on_delete=models.CASCADE, related_name='+', blank=True, null=True)
    assigned_object_id = models.PositiveBigIntegerField(blank=True, null=True)
    assigned_object = GenericForeignKey(ct_field='assigned_object_type', fk_field='assigned_object_id')
    zabbixconfigurationgroup = models.ForeignKey('nbxsync.ZabbixConfigurationGroup', on_delete=models.SET_NULL, blank=True, null=True)

    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.SET_NULL)

    class Meta:
        verbose_name = 'Zabbix Macro Assignment'
        verbose_name_plural = 'Zabbix Macro Assignments'
        ordering = ('-created',)

        constraints = [
            models.UniqueConstraint(
                fields=['zabbixmacro', 'is_regex', 'context', 'value', 'assigned_object_type', 'assigned_object_id'],
                name='%(app_label)s_%(class)s_unique__macroassignment_per_object',
                violation_error_message='Macro can only be assigned once to a given object',
            )
        ]

    def clean(self):
        super().clean()
        if self.assigned_object_type is None or self.assigned_object_id is None:
            raise ValidationError('An assigned object must be provided')

        if self.is_regex and self.context == '':
            raise ValidationError('A context must be provided when the macro is a regex')

        if self.is_regex and self.value == '':
            raise ValidationError('A value must be provided when the macro is a regex')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.context:
            if self.is_regex:
                return f'{self.zabbixmacro.macro[:-1]}:regex:"{self.context}"}}'
            return f'{self.zabbixmacro.macro[:-1]}:{self.context}}}'
        return self.zabbixmacro.macro

    def is_template(self):
        return bool(TEMPLATE_PATTERN.search(self.value))

    def render(self, **context):
        if isinstance(self.assigned_object, ZabbixConfigurationGroup):
            return self.value, True

        context = self.get_context(**context)

        try:
            output = render_jinja2(self.value, context)
            output = output.replace('\r\n', '\n')
            return output, True

        except TemplateSyntaxError as err:
            return self.value, False

        except UndefinedError as err:
            return self.value, False

        except TemplateError as err:
            return self.value, False

        except Exception as err:
            return self.value, False

    def get_context(self, **extra_context):
        context = {
            'object': self.assigned_object,
            'macro': self.zabbixmacro.macro,
            'value': self.value,
            'description': self.zabbixmacro.description,
        }
        context.update(extra_context)
        return context

    @property
    def full_name(self):
        return self
