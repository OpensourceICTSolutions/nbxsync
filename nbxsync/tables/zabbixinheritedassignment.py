import django_tables2 as tables
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from nbxsync.constants import INHERITANCE_SOURCE_COLORS, PATH_LABELS
from nbxsync.models import ZabbixConfigurationGroup

__all__ = ('ZabbixInheritedAssignmentTable',)


class ZabbixInheritedAssignmentTable(tables.Table):
    # inherited_from = tables.Column(empty_values=(), verbose_name=_('Inherited From'))
    inherited_from = tables.Column(empty_values=(), verbose_name=_('Inherited From'), orderable=False)

    def render_inherited_from(self, record):
        if getattr(record, '_inherited_from', None):
            source = getattr(record, '_inherited_from', None)
            label = source.replace('_', ' ').title()
            resolved_label = PATH_LABELS.get(label.lower(), label)
            color = INHERITANCE_SOURCE_COLORS.get(source, 'secondary')
            return mark_safe(f'<span class="badge bg-{color} text-dark">{resolved_label}</span>')

        assigned = getattr(record, 'assigned_object', None)

        # If the related object is a ZabbixConfigurationGroup, don’t render any inheritance badge.
        if getattr(record, 'zabbixconfigurationgroup', None) and not isinstance(assigned, ZabbixConfigurationGroup):
            source = getattr(record, 'zabbixconfigurationgroup', None)
            label = 'zabbixconfigurationgroup'
            resolved_label = PATH_LABELS.get(label.lower(), label)
            color = INHERITANCE_SOURCE_COLORS.get(source, 'secondary')
            return mark_safe(f'<span class="badge bg-{color} text-dark">{resolved_label}</span>')

        return ''
