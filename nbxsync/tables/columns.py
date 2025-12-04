import django_tables2 as tables
from django.contrib.contenttypes.models import ContentType
from django.utils.text import capfirst

from netbox.tables.columns import ActionsColumn
from nbxsync.models import ZabbixConfigurationGroup

__all__ = ('InheritanceAwareActionsColumn', 'ContentTypeModelNameColumn')


class InheritanceAwareActionsColumn(ActionsColumn):
    def render(self, **kwargs):
        # Always let the base class run first so it can call extra_buttons
        html = super().render(**kwargs)

        record = kwargs.get('record')

        if record.assigned_object_type_id == ContentType.objects.get_for_model(ZabbixConfigurationGroup).id:
            return html

        # If the object for this row has the attribute _inherited_from or zabbixconfigurationgroup
        # Hide the 'Actions' cell, so the user has no easy way to edit this row (as we dont want that)
        if getattr(record, '_inherited_from', None) or getattr(record, 'zabbixconfigurationgroup', None):
            return ''
        return html


class ContentTypeModelNameColumn(tables.Column):
    """
    Renders a ContentType as just the model's verbose_name (e.g. 'Device'),
    instead of 'app | Model'.
    """

    def render(self, value):
        if not value:
            return '-'
        model = value.model_class()
        # Fallback if the model class isn't importable
        if model is None:
            return capfirst(value.model.replace('_', ' '))
        return capfirst(model._meta.verbose_name)
