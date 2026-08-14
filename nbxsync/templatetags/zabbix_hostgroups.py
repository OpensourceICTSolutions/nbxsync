from django import template


register = template.Library()


@register.simple_tag(takes_context=True)
def render_zabbix_hostgroup_assignment(context, assignment, **extra):
    """Render a ZabbixHostgroupAssignment value for display.

    Sync passes ``object=<Device/VM>`` explicitly. Without that override,
    ``assignment.render`` uses the assignment target in device-shaped form
    (see ``wrap_assignment_object``). When the target cannot satisfy the
    template (e.g. ``Roles/{{ object.role.name }}`` on a SiteGroup), show the
    raw template string — never a sample from an unrelated descendant device.
    """
    if 'object' not in extra:
        request_object = context.get('object')
        if request_object is not None and _is_device_like(request_object):
            extra['object'] = request_object

    output, success = assignment.render(**extra)
    if success:
        return output
    if assignment.is_template():
        return assignment.zabbixhostgroup.value
    return ''


def _is_device_like(obj) -> bool:
    from dcim.models import Device, VirtualDeviceContext
    from virtualization.models import VirtualMachine

    return isinstance(obj, Device | VirtualMachine | VirtualDeviceContext)
