"""Device-shaped Jinja context for hierarchy-level hostgroup/tag assignments.

Sync always passes the Device/VM as ``object`` (see HostSync). UI preview and
HostGroupSync render against the assignment target itself. Templates in the
wild are written for the device-shaped namespace (``object.role.name``,
``object.site.name``, …), so a DeviceRole/Site/Platform target must expose
those same paths — not by borrowing an arbitrary descendant device, but by
wrapping the target so its own identity fills the matching slot.

Targets that cannot fill a single unambiguous device-shaped value (SiteGroup,
Region, Manufacturer, …) are returned unchanged; templates that need a Device
then fail cleanly and the UI shows the raw template string.

``related_template_context`` adds the #102 shorthand keys (``device``,
``site``, ``tenant``, ``role``, ``device_type``, ``manufacturer``) from that
same render object.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


_DEVICE_LIKE = frozenset({'Device', 'VirtualMachine', 'VirtualDeviceContext'})


def wrap_assignment_object(target: Any) -> Any:
    """Return ``target`` in the namespace device-context Jinja templates expect.

    Explicit ``object=`` overrides from sync are applied by the caller after
    this helper runs, so this only affects the default (assignment-target)
    render path.
    """
    if target is None:
        return None

    model_name = type(target).__name__
    if model_name in _DEVICE_LIKE:
        return target

    if model_name == 'DeviceRole':
        # Roles/{{ object.role.name }} and Roles/{{ object.name }}
        return SimpleNamespace(role=target, name=getattr(target, 'name', str(target)))

    if model_name == 'Platform':
        return SimpleNamespace(platform=target, name=getattr(target, 'name', str(target)))

    if model_name == 'Site':
        # Sites/{{ object.site.group.name }}/{{ object.site.name }}
        return SimpleNamespace(site=target, name=getattr(target, 'name', str(target)))

    if model_name == 'Cluster':
        return SimpleNamespace(cluster=target, name=getattr(target, 'name', str(target)))

    if model_name == 'ClusterType':
        return SimpleNamespace(cluster=SimpleNamespace(type=target), name=getattr(target, 'name', str(target)))

    if model_name == 'DeviceType':
        return SimpleNamespace(device_type=target, name=getattr(target, 'name', str(target)))

    if model_name == 'Manufacturer':
        return SimpleNamespace(
            device_type=SimpleNamespace(manufacturer=target),
            name=getattr(target, 'name', str(target)),
        )

    # SiteGroup / Region / unknown: no single device-shaped binding.
    return target


_RELATED_ATTRS = ('site', 'tenant', 'role', 'device_type')


def related_template_context(obj: Any) -> dict[str, Any]:
    """Top-level Jinja aliases for related NetBox objects (#102).

    Derived from the render ``object`` — the Device/VM/VDC during host sync,
    or the (possibly wrapped) assignment target in the UI preview. Never from
    the assignment row itself: a Role-level tag rendered with ``object=device``
    must expose that device's site/role, not the Role assignment target.

    ``device`` is set only for Device/VM/VDC hosts. Hierarchy previews omit it
    so a Site assignment is not advertised as ``device``. Missing attributes
    are omitted so templates fail cleanly.
    """
    if obj is None:
        return {}

    context: dict[str, Any] = {}
    if type(obj).__name__ in _DEVICE_LIKE:
        context['device'] = obj

    for attr in _RELATED_ATTRS:
        value = getattr(obj, attr, None)
        if value is not None:
            context[attr] = value

    device_type = context.get('device_type')
    manufacturer = getattr(device_type, 'manufacturer', None) if device_type is not None else None
    if manufacturer is not None:
        context['manufacturer'] = manufacturer

    return context
