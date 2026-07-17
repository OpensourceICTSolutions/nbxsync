from django import template
from nbxsync.utils.preview import get_representative_device


register = template.Library()


@register.simple_tag(takes_context=True)
def render_zabbix_tag_assignment(context, assignment, **extra):
    """Render a ZabbixTagAssignment's value for preview display.

    Mirrors ``render_zabbix_hostgroup_assignment``: substitute a
    representative Device/VM when no explicit ``object`` was supplied so that
    device-context templates (``object.role.name``, ``object.site.name``, …)
    resolve in the UI the same way they do during Zabbix sync.
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
    return ''


def _is_device_like(obj) -> bool:
    from dcim.models import Device, VirtualDeviceContext
    from virtualization.models import VirtualMachine
    return isinstance(obj, Device | VirtualMachine | VirtualDeviceContext)
