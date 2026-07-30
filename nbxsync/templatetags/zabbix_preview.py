from django import template

from nbxsync.utils.preview import get_representative_device

register = template.Library()


@register.simple_tag
def zabbix_preview_representative(assignment):
    """The Device/VM a hierarchy-level preview value was rendered with.

    Values assigned to a Site, Role, Platform, ... are rendered per inherited
    Device/VM during sync, so the UI can only show one example. Returning the
    representative lets templates disclose which object produced the value
    instead of presenting it as the single truth. Empty string when the
    assignment targets a Device/VM directly, or when nothing inherits it.
    """
    target = assignment.assigned_object
    if target is None:
        return ''
    if type(target).__name__ in ('Device', 'VirtualMachine', 'VirtualDeviceContext'):
        return ''
    representative = get_representative_device(assignment)
    return str(representative) if representative is not None else ''
