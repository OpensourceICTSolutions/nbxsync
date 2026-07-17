"""Helpers for rendering Jinja2 preview values in the NetBox UI.

When a hostgroup/tag assignment is assigned to a non-Device target
(DeviceRole, SiteGroup, Site, Region, Manufacturer, Platform), the template
is conceptually rendered "per inherited Device/VM" during Zabbix sync.
The NetBox UI detail page / ObjectViewTable only has the assignment object,
so templates that traverse device-level attributes (``object.role.name``,
``object.site.group.name``, ...) fail with UndefinedError.

These helpers pick a **representative** Device/VM from the assignment's
descendants so the preview renders the same value the sync engine would
produce. The representative is arbitrary — the UI shows the rendered value
cleanly, as if it were static.
"""
from __future__ import annotations

import functools
from typing import TYPE_CHECKING

from dcim.models import Device, Site
from virtualization.models import VirtualMachine


if TYPE_CHECKING:
    # Avoid circular import at module load — assignment is only a type hint.
    from nbxsync.models import ZabbixHostgroupAssignment, ZabbixTagAssignment

_SENTINEL = object()  # marks a cached "None" so we don't re-query


def get_representative_device(
    assignment: ZabbixHostgroupAssignment | ZabbixTagAssignment,
) -> Device | VirtualMachine | None:
    """Return a Device/VM that inherits ``assignment``, for preview rendering.

    Returns ``None`` if the assignment target is itself a Device/VM, or if no
    matching Device/VM exists. The caller decides what to do with ``None``
    (typically: fall back to the legacy behaviour of rendering against the
    assignment target).
    """
    target = assignment.assigned_object
    if target is None:
        return None

    model_name = type(target).__name__

    # Direct assignment — the target IS the device/VM, no lookup needed.
    if model_name in ('Device', 'VirtualMachine', 'VirtualDeviceContext'):
        return target

    resolved = _resolve_cached(model_name, target.pk)
    return None if resolved is _SENTINEL else resolved


@functools.lru_cache(maxsize=64)
def _resolve_cached(model_name: str, target_pk: int):
    """Resolve a representative device for an assignment target.

    Cached on ``(model_name, target_pk)`` — the ObjectViewTable renders
    each row against a different assignment, so ``maxsize=64`` covers a
    typical page without unbounded growth. ``None`` results are stored as
    ``_SENTINEL`` to avoid re-querying empty roles/sites on every row.
    """
    resolver = _RESOLVERS.get(model_name)
    if resolver is None:
        return _SENTINEL
    return resolver(target_pk) or _SENTINEL


def _fetch(model, **lookup):
    """Fetch a single object or None."""
    return model.objects.filter(**lookup).first()


def _resolve_role(pk):
    from dcim.models import DeviceRole
    role = _fetch(DeviceRole, pk=pk)
    if role is None:
        return None
    return (_fetch(Device, role=role)
            or _fetch(VirtualMachine, role=role))


def _resolve_platform(pk):
    from dcim.models import Platform
    platform = _fetch(Platform, pk=pk)
    if platform is None:
        return None
    return (_fetch(Device, platform=platform)
            or _fetch(VirtualMachine, platform=platform))


def _resolve_manufacturer(pk):
    from dcim.models import Manufacturer
    mfr = _fetch(Manufacturer, pk=pk)
    if mfr is None:
        return None
    return _fetch(Device, device_type__manufacturer=mfr)


def _resolve_device_type(pk):
    from dcim.models import DeviceType
    dt = _fetch(DeviceType, pk=pk)
    if dt is None:
        return None
    return _fetch(Device, device_type=dt)


def _resolve_site(pk):
    from dcim.models import Site as SiteModel
    site = _fetch(SiteModel, pk=pk)
    if site is None:
        return None
    return (_fetch(Device, site=site)
            or _fetch(VirtualMachine, cluster__site=site))


def _resolve_sitegroup_or_region(pk):
    from dcim.models import Region, SiteGroup
    group = _fetch(SiteGroup, pk=pk) or _fetch(Region, pk=pk)
    if group is None:
        return None
    return _device_under_tree(group)


def _resolve_cluster(pk):
    from virtualization.models import Cluster
    cluster = _fetch(Cluster, pk=pk)
    if cluster is None:
        return None
    return (_fetch(Device, cluster=cluster)
            or _fetch(VirtualMachine, cluster=cluster))


def _resolve_cluster_type(pk):
    from virtualization.models import ClusterType
    ct = _fetch(ClusterType, pk=pk)
    if ct is None:
        return None
    return (_fetch(Device, cluster__type=ct)
            or _fetch(VirtualMachine, cluster__type=ct))


# Dispatch table — keeps _resolve_cached's McCabe complexity low.
_RESOLVERS = {
    'DeviceRole': _resolve_role,
    'Platform': _resolve_platform,
    'Manufacturer': _resolve_manufacturer,
    'DeviceType': _resolve_device_type,
    'Site': _resolve_site,
    'SiteGroup': _resolve_sitegroup_or_region,
    'Region': _resolve_sitegroup_or_region,
    'Cluster': _resolve_cluster,
    'ClusterType': _resolve_cluster_type,
}


def _device_under_tree(group_or_region) -> Device | VirtualMachine | None:
    """Find a device under a SiteGroup or Region (recursively)."""
    if hasattr(group_or_region, 'get_descendants'):
        descendant_pks = list(
            group_or_region.get_descendants()
            .values_list('pk', flat=True)
        )
        group_ids = [group_or_region.pk] + descendant_pks
    else:
        group_ids = [group_or_region.pk]

    site_ids = list(
        Site.objects.filter(group__in=group_ids)
        .values_list('pk', flat=True)
    )
    if not site_ids:
        return None

    dev = Device.objects.filter(site__in=site_ids).first()
    if dev:
        return dev

    return VirtualMachine.objects.filter(
        cluster__site__in=site_ids
    ).first()
