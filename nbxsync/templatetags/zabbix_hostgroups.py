from django import template
from nbxsync.utils.preview import get_representative_device


register = template.Library()


@register.simple_tag(takes_context=True)
def render_zabbix_hostgroup_assignment(context, assignment, **extra):
    """Render a ZabbixHostgroupAssignment's value for preview display.

    If the caller did not pass an explicit ``object`` (the normal case for
    UI rendering), substitute a representative Device/VM so device-context
    templates like ``object.role.name`` and ``object.site.group.name`` can
    resolve. The sync engine already passes the Device explicitly, so this
    only affects the preview path.
    """
    if 'object' not in extra:
        request_object = context.get('object')
        if request_object is None or not _is_device_like(request_object):
            representative = get_representative_device(assignment)
            if representative is not None:
                extra['object'] = representative
        else:
            extra['object'] = request_object

    output, success = assignment.render(**extra)
    if success:
        return output
    # Render failed even with the representative (or no representative found).
    return ''


def _is_device_like(obj) -> bool:
    from dcim.models import Device, VirtualDeviceContext
    from virtualization.models import VirtualMachine

    return isinstance(obj, Device | VirtualMachine | VirtualDeviceContext)
