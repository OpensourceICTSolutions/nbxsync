import django_tables2 as tables
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from nbxsync.constants import INHERITANCE_SOURCE_COLORS

__all__ = ('ZabbixInheritedAssignmentTable',)


class ZabbixInheritedAssignmentTable(tables.Table):
    inherited_from = tables.Column(empty_values=(), verbose_name=_('Inherited From'), orderable=False)

    def render_inherited_from(self, record):
        source = getattr(record, '_inherited_from', None)
        if not source:
            return ''
        label = source.replace('_', ' ').title()
        color = INHERITANCE_SOURCE_COLORS.get(source, 'secondary')
        return mark_safe(f'<span class="badge bg-{color} text-dark">{label}</span>')
