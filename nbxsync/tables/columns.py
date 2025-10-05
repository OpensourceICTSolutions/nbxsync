import django_tables2 as tables
from django.utils.safestring import mark_safe
from django.utils.text import capfirst

from netbox.tables.columns import ActionsColumn

__all__ = ('InheritanceAwareActionsColumn', 'ContentTypeModelNameColumn')


class InheritanceAwareActionsColumn(ActionsColumn):
    def render(self, **kwargs):
        # Always let the base class run first so it can call extra_buttons
        html = super().render(**kwargs)

        record = kwargs.get('record')
        if getattr(record, '_inherited_from', None):
            # Suppress the whole cell for inherited records (after callbacks ran)
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
