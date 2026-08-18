from django import template


register = template.Library()


@register.simple_tag(takes_context=True)
def render_zabbix_tag_assignment(context, assignment, **extra):
    """Render a ZabbixTagAssignment value for display.

    Mirrors ``render_zabbix_hostgroup_assignment``: assignment-target context
    with device-shaped wrapping; raw template on unresolvable hierarchy targets.
    """
    if 'object' not in extra:
        request_object = context.get('object')
        if request_object is not None and _is_device_like(request_object):
            extra['object'] = request_object

    output, success = assignment.render(**extra)
    if success:
        return output
    if assignment.is_template():
        return assignment.zabbixtag.value
    return ''


def _is_device_like(obj) -> bool:
    from dcim.models import Device, VirtualDeviceContext
    from virtualization.models import VirtualMachine

    return isinstance(obj, Device | VirtualMachine | VirtualDeviceContext)
