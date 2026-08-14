import logging

from django.contrib.contenttypes.models import ContentType

from nbxsync.models import ZabbixHostBinding, ZabbixServerAssignment
from nbxsync.utils import get_assigned_zabbixobjects
from nbxsync.utils.host_binding import HostBindingDeleteProxy, iter_host_bindings
from nbxsync.utils.sync import HostSync
from nbxsync.utils.sync.safe_delete import safe_delete

logger = logging.getLogger(__name__)

__all__ = ('DeleteHostJob',)


class DeleteHostJob:
    def __init__(self, **kwargs):
        self.binding_ids = tuple(kwargs.get('binding_ids') or ())
        self.instance = kwargs.get('instance')

    def _bindings(self):
        if self.binding_ids:
            return ZabbixHostBinding.objects.filter(pk__in=self.binding_ids).select_related(
                'zabbixserver',
                'assigned_object_type',
            )
        if self.instance is not None:
            return iter_host_bindings(self.instance)
        return ZabbixHostBinding.objects.none()

    def run(self):
        failures = []
        servers_seen = set()

        # Binding-based deletes intentionally omit sync_enabled checks.
        # Deleting a Device/VM in NetBox is inventory retirement: the Zabbix
        # host must go even if automatic sync was disabled on the assignment
        # or server. The legacy path below still respects sync_enabled.
        for binding in self._bindings():
            servers_seen.add(binding.zabbixserver_id)
            assigned_object = self.instance if self.instance is not None else binding.assigned_object
            proxy = HostBindingDeleteProxy(binding, assigned_object=assigned_object)
            extra_args = {'all_objects': {'_instance': assigned_object}} if assigned_object is not None else None
            try:
                safe_delete(HostSync, proxy, **({'extra_args': extra_args} if extra_args else {}))
            except Exception as exc:
                failures.append((binding.pk, exc))
                logger.warning('Failed to delete bound host %s: %s', binding, exc)

        # Legacy compatibility: jobs queued before deletion signals captured
        # binding IDs pass an instance here (no binding_ids). Fall back to
        # resolving assignments from the instance directly. Safe to remove
        # once no pre-binding-ID RQ jobs remain in-flight.
        if self.instance is not None and not self.binding_ids:
            self._delete_legacy_assignments(servers_seen, failures)

        if failures:
            binding_ids = ', '.join(str(binding_id) for binding_id, _ in failures)
            raise RuntimeError(f'Failed to delete Zabbix host bindings: {binding_ids}')

    def _delete_legacy_assignments(self, servers_seen, failures):
        extra_args = {'all_objects': {'_instance': self.instance}}
        try:
            all_objects = get_assigned_zabbixobjects(self.instance)
            server_assignments = all_objects.get('server_assignments', [])
        except Exception:
            logger.exception('Failed to resolve inherited assignments for %s; using direct assignments only.', self.instance)
            instance_ct = ContentType.objects.get_for_model(self.instance)
            server_assignments = ZabbixServerAssignment.objects.filter(
                assigned_object_type=instance_ct,
                assigned_object_id=self.instance.pk,
            ).select_related('zabbixserver')

        for assignment in server_assignments:
            if assignment.zabbixserver_id in servers_seen:
                continue
            if not assignment.sync_enabled or not assignment.zabbixserver.sync_enabled:
                continue
            servers_seen.add(assignment.zabbixserver_id)
            try:
                safe_delete(HostSync, assignment, extra_args=extra_args)
            except Exception as exc:
                failures.append((f'legacy:{assignment.pk}', exc))
                logger.warning('Failed to delete host for %s via assignment %s: %s', self.instance, assignment, exc)
