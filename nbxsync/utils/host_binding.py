import logging

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction

from nbxsync.models import ZabbixHostBinding
from nbxsync.settings import get_plugin_settings

logger = logging.getLogger(__name__)

__all__ = (
    'get_host_binding',
    'set_host_binding',
    'delete_host_binding',
    'delete_host_binding_by_id',
    'iter_host_bindings',
    'backfill_or_resolve_conflict',
    'HostBindingDeleteProxy',
)


def get_host_binding(instance, zabbixserver):
    """Return the ZabbixHostBinding for a given NetBox object and server, if any."""
    ct = ContentType.objects.get_for_model(instance)
    return ZabbixHostBinding.objects.filter(
        zabbixserver=zabbixserver,
        assigned_object_type=ct,
        assigned_object_id=instance.pk,
    ).first()


def set_host_binding(instance, zabbixserver, hostid, hostname=''):
    """Create or update the binding for ``instance`` -> ``hostid``.

    Raises ``RuntimeError`` if the hostid is already bound to another object
    on the same server (duplicate managed identity).
    """
    ct = ContentType.objects.get_for_model(instance)
    try:
        # Own savepoint so a uniqueness conflict does not abort an outer atomic block.
        with transaction.atomic():
            binding, _ = ZabbixHostBinding.objects.update_or_create(
                zabbixserver=zabbixserver,
                assigned_object_type=ct,
                assigned_object_id=instance.pk,
                defaults={'hostid': hostid, 'hostname': hostname},
            )
    except IntegrityError as exc:
        raise RuntimeError(f'Host binding conflict for {instance} on {zabbixserver}: hostid {hostid} or object is already bound to another host') from exc
    return binding


def delete_host_binding(instance, zabbixserver=None):
    """Remove all bindings for ``instance``, optionally scoped to one server."""
    ct = ContentType.objects.get_for_model(instance)
    qs = ZabbixHostBinding.objects.filter(assigned_object_type=ct, assigned_object_id=instance.pk)
    if zabbixserver is not None:
        qs = qs.filter(zabbixserver=zabbixserver)
    qs.delete()


def delete_host_binding_by_id(binding_id):
    """Delete one binding after its remote host has been retired successfully."""
    ZabbixHostBinding.objects.filter(pk=binding_id).delete()


def iter_host_bindings(instance):
    """Iterate over all bindings for ``instance``."""
    ct = ContentType.objects.get_for_model(instance)
    return ZabbixHostBinding.objects.filter(
        assigned_object_type=ct,
        assigned_object_id=instance.pk,
    ).select_related('zabbixserver')


def _host_tags_to_dict(host):
    return {tag['tag']: tag['value'] for tag in host.get('tags', [])}


def _expected_source_tags(instance):
    pluginsettings = get_plugin_settings()
    return {
        pluginsettings.objtag_type: str(type(instance).__name__).lower(),
        pluginsettings.objtag_id: str(instance.pk),
    }


def backfill_or_resolve_conflict(instance, zabbixserver, api, hostname=None):
    """Adopt an existing Zabbix host by its managed source tags.

    If no host with the same technical name exists, returns ``None`` so the
    caller can create a new one. If an unmanaged host with the same name
    exists, or if the matching host belongs to another NetBox object, a
    ``RuntimeError`` is raised.

    ``hostname`` must be the technical host name actually sent to Zabbix
    (custom-field hostname when set, then sanitized) — the same value
    ``HostSync.get_name_value()`` / ``sanitize_string()`` produce. Falling back
    to the raw NetBox name would miss renamed or custom-hostname hosts.

    Adoption is gated by the ``adopt_existing_hosts`` setting: taking over a
    host makes NetBox authoritative over its configuration, so operators opt in
    explicitly instead of discovering it after the first sync.
    """
    if hostname is None:
        name = str(instance.name) if hasattr(instance, 'name') else str(instance)
    else:
        name = str(hostname)
    hosts = api.host.get(filter={'host': name}, selectTags='extend')
    if isinstance(hosts, dict):
        hosts = hosts.get('result', [])

    if not hosts:
        return None

    expected = _expected_source_tags(instance)
    matches = [host for host in hosts if all(_host_tags_to_dict(host).get(k) == v for k, v in expected.items())]

    if len(matches) == 1:
        if not get_plugin_settings().adopt_existing_hosts:
            raise RuntimeError(f'Zabbix host "{name}" (hostid {matches[0]["hostid"]}) already carries the managed identity for {instance} but is not bound in NetBox. Set nbxsync adopt_existing_hosts = True to let nbxsync take ownership of it, or remove the host from Zabbix first.')
        logger.info('Adopting existing Zabbix host %s (hostid %s) for %s on %s', name, matches[0]['hostid'], instance, zabbixserver)
        return int(matches[0]['hostid'])

    if len(hosts) == 1 and not matches:
        raise RuntimeError(f'Unmanaged host conflict: a Zabbix host named "{name}" exists but does not match the managed identity for {instance}.')

    raise RuntimeError(f'Ambiguous host conflict: {len(hosts)} Zabbix hosts found with name "{name}".')


class HostBindingDeleteProxy:
    """Assignment-like delete target backed by a durable host binding."""

    _is_inherited_copy = False

    def __init__(self, binding, assigned_object=None):
        self.binding_id = binding.pk
        self.zabbixserver = binding.zabbixserver
        self.hostid = binding.hostid
        self.assigned_object = assigned_object if assigned_object is not None else binding.assigned_object
        self.assigned_object_type = binding.assigned_object_type
        self.assigned_object_id = binding.assigned_object_id

    def update_sync_info(self, *args, **kwargs):
        pass

    def save(self, *args, **kwargs):
        pass
