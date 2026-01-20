import logging
import re

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from jinja2 import TemplateError, TemplateSyntaxError, UndefinedError

from netbox.models import NetBoxModel
from utilities.jinja2 import render_jinja2

from nbxsync.constants import ASSIGNMENT_MODELS, CONFIGGROUP_OBJECTS
from nbxsync.models import ZabbixConfigurationGroup

__all__ = ('ZabbixTagAssignment',)

TEMPLATE_PATTERN = re.compile(r'({{.*?}}|{%-?\s*.*?\s*-?%}|{#.*?#})')


class ZabbixTagAssignment(NetBoxModel):
    zabbixtag = models.ForeignKey(to='nbxsync.ZabbixTag', on_delete=models.CASCADE, related_name='zabbixtagassignment')
    assigned_object_type = models.ForeignKey(to=ContentType, limit_choices_to=(ASSIGNMENT_MODELS | CONFIGGROUP_OBJECTS), on_delete=models.CASCADE, related_name='+', blank=True, null=True)
    assigned_object_id = models.PositiveBigIntegerField(blank=True, null=True)
    assigned_object = GenericForeignKey(ct_field='assigned_object_type', fk_field='assigned_object_id')
    zabbixconfigurationgroup = models.ForeignKey('nbxsync.ZabbixConfigurationGroup', on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        verbose_name = 'Zabbix Tag Assignment'
        verbose_name_plural = 'Zabbix Tag Assignments'
        ordering = ('-created',)

        constraints = [
            models.UniqueConstraint(
                fields=['zabbixtag', 'assigned_object_type', 'assigned_object_id'],
                name='%(app_label)s_%(class)s_unique__tag_per_object',
                violation_error_message='A tag can only be assigned once to a given object',
            )
        ]

    def render(self, **context):
        context = self.get_context(**context)

        if isinstance(self.assigned_object, ZabbixConfigurationGroup):
            return self.zabbixtag.value, True

        try:
            output = render_jinja2(self.zabbixtag.value, context)
            output = output.replace('\r\n', '\n')
            return output, True

        except TemplateSyntaxError as err:
            error_msg = f"Template syntax error in '{self.zabbixtag.value}': {str(err)}"
            return '', False

        except UndefinedError as err:
            error_msg = f"Undefined variable in template '{self.zabbixtag.value}': {str(err)}"
            return '', False

        except TemplateError as err:
            error_msg = f"Template error in '{self.zabbixtag.value}': {str(err)}"
            return '', False

        except Exception as err:
            error_msg = f"Unexpected error rendering template '{self.zabbixtag.value}': {str(err)}"
            return '', False

    def is_template(self):
        return bool(TEMPLATE_PATTERN.search(self.zabbixtag.value))

    def clean(self):
        super().clean()

        if self.assigned_object_type is None or self.assigned_object_id is None:
            raise ValidationError('An assigned object must be provided')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def get_context(self, **extra_context):
        context = {
            'object': self.assigned_object,
            'tag': self.zabbixtag.tag,
            'value': self.zabbixtag.value,
            'name': self.zabbixtag.name,
            'description': self.zabbixtag.description,
        }
        context.update(extra_context)
        return context

    def __str__(self):
        ret_val = ''
        if self.assigned_object:
            if hasattr(self.assigned_object, 'name'):
                ret_val = f'{str(self.zabbixtag.name)} - {str(self.assigned_object.name)}'
            else:
                ret_val = f'{str(self.zabbixtag.name)} - {str(self.assigned_object)}'

        return ret_val
