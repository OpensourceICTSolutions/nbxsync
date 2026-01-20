import re

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from jinja2 import TemplateError, TemplateSyntaxError, UndefinedError

from netbox.models import NetBoxModel
from utilities.jinja2 import render_jinja2

from nbxsync.constants import ASSIGNMENT_MODELS, CONFIGGROUP_OBJECTS
from nbxsync.models import SyncInfoModel, ZabbixConfigurationGroup


__all__ = ('ZabbixHostgroupAssignment',)

TEMPLATE_PATTERN = re.compile(r'({{.*?}}|{%-?\s*.*?\s*-?%}|{#.*?#})')


class ZabbixHostgroupAssignment(SyncInfoModel, NetBoxModel):
    zabbixhostgroup = models.ForeignKey('nbxsync.ZabbixHostgroup', on_delete=models.CASCADE, related_name='zabbixhostgroupassignment')
    zabbixconfigurationgroup = models.ForeignKey('nbxsync.ZabbixConfigurationGroup', on_delete=models.SET_NULL, blank=True, null=True)

    assigned_object_type = models.ForeignKey(to=ContentType, limit_choices_to=(ASSIGNMENT_MODELS | CONFIGGROUP_OBJECTS), on_delete=models.CASCADE, related_name='+', blank=True, null=True)
    assigned_object_id = models.PositiveBigIntegerField(blank=True, null=True)
    assigned_object = GenericForeignKey(ct_field='assigned_object_type', fk_field='assigned_object_id')

    class Meta:
        verbose_name = 'Zabbix Hostgroup Assignment'
        verbose_name_plural = 'Zabbix Hostgroup Assignments'
        ordering = ('-created',)

        constraints = [
            models.UniqueConstraint(
                fields=['zabbixhostgroup', 'assigned_object_type', 'assigned_object_id'],
                name='%(app_label)s_%(class)s_unique__hostgroupassignment_per_object',
                violation_error_message='Hostgroup can only be assigned once to a given object',
            )
        ]

    def clean(self):
        if self.assigned_object_type is None or self.assigned_object_id is None:
            raise ValidationError('An assigned object must be provided')
        super().clean()

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def get_context(self, **extra_context):
        context = {
            'object': self.assigned_object,
            'value': self.zabbixhostgroup.value,
            'name': self.zabbixhostgroup.name,
        }
        context.update(extra_context)
        return context

    def render(self, **context):
        context = self.get_context(**context)

        if isinstance(self.assigned_object, ZabbixConfigurationGroup):
            return self.zabbixhostgroup.value, True

        try:
            output = render_jinja2(self.zabbixhostgroup.value, context)
            output = output.replace('\r\n', '\n')
            return output, True

        except TemplateSyntaxError as err:
            error_msg = f"Template syntax error in '{self.zabbixhostgroup.value}': {str(err)}"
            return error_msg, False

        except UndefinedError as err:
            error_msg = f"Undefined variable in template '{self.zabbixhostgroup.value}': {str(err)}"
            return error_msg, False

        except TemplateError as err:
            error_msg = f"Template error in '{self.zabbixhostgroup.value}': {str(err)}"
            return error_msg, False

        except Exception as err:
            error_msg = f"Unexpected error rendering template '{self.zabbixhostgroup.value}': {str(err)}"
            return error_msg, False

    def is_template(self):
        return bool(TEMPLATE_PATTERN.search(self.zabbixhostgroup.value))

    def __str__(self):
        ret_val = str(self.zabbixhostgroup.name)
        if self.assigned_object:
            ret_val = f'{ret_val} - {str(self.assigned_object)}'

        return ret_val
