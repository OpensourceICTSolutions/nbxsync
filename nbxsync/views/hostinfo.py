import logging

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from nbxsync.constants.assignment_type_to_field import OBJECT_TYPE_MODEL_MAP
from nbxsync.tables import ZabbixEventTable, ZabbixProblemTable
from nbxsync.utils import ZabbixConnection
from nbxsync.utils.host_binding import iter_managed_hosts

logger = logging.getLogger(__name__)


def _resolve_model_or_404(objtype):
    """Look up the NetBox model for an objtype URL segment, or raise 404."""
    model = OBJECT_TYPE_MODEL_MAP.get(objtype)
    if not model:
        raise Http404(_('Unsupported object type: %(objtype)s') % {'objtype': objtype})
    return model


def _managed_hosts_for(model, pk):
    """Return managed (server, hostid) identities for the given (model, pk)."""
    instance = get_object_or_404(model, pk=pk)
    return list(iter_managed_hosts(instance, require_hostid=True))


def _event_row(assignment, event, *, end_time, duration):
    """
    Build one table row from a Zabbix event dict.

    Both the recovered-event branch and the still-open-event branch use this
    so they cannot drift in field shape over time.
    """
    return {
        'zabbixserver': assignment.zabbixserver,
        'acknowledged': event.get('acknowledged', '0'),
        'duration': duration,
        'event': event.get('name'),
        'eventid': event.get('eventid'),
        'triggerid': event.get('objectid'),
        'severity': event.get('severity'),
        'start_time': event.get('clock'),
        'end_time': end_time,
        'opdata': event.get('opdata'),
    }


class ZabbixHostProblemsView(TemplateView):
    template_name = 'nbxsync/modals/op_view.html'

    def get_context_data(self, objtype, pk, **kwargs):
        context = super().get_context_data(**kwargs)
        model = _resolve_model_or_404(objtype)

        problem_list = []
        fetch_errors = []

        for assignment in _managed_hosts_for(model, pk):
            if not assignment.hostid:
                continue

            try:
                with ZabbixConnection(assignment.zabbixserver) as api:
                    problems = api.problem.get(hostids=assignment.hostid, sortfield='eventid', sortorder='DESC')
                    for problem in problems:
                        problem_list.append(
                            {'zabbixserver': assignment.zabbixserver, 'eventid': problem.get('eventid'), 'triggerid': problem.get('objectid'), 'severity': problem.get('severity'), 'clock': problem.get('clock'), 'problem': problem.get('name'), 'acknowledged': problem.get('acknowledged'), 'opdata': problem.get('opdata')}
                        )
            except Exception:
                logger.exception('Failed to fetch Zabbix problems for host %s on server %s', assignment.hostid, assignment.zabbixserver)
                fetch_errors.append(assignment.zabbixserver)

        context['table'] = ZabbixProblemTable(problem_list)
        context['fetch_errors'] = fetch_errors
        return context


class ZabbixHostEventsView(TemplateView):
    template_name = 'nbxsync/modals/op_view.html'

    def get_context_data(self, objtype, pk, **kwargs):
        context = super().get_context_data(**kwargs)
        model = _resolve_model_or_404(objtype)

        # Accumulated across all Zabbix servers this device is assigned to;
        # deliberately declared outside the per-server loop so servers
        # after the first are not clobbered.
        event_list = []
        fetch_errors = []

        for assignment in _managed_hosts_for(model, pk):
            if not assignment.hostid:
                continue

            try:
                with ZabbixConnection(assignment.zabbixserver) as api:
                    events = api.event.get(hostids=assignment.hostid, limit=15, sortfield=['clock', 'eventid'], sortorder='DESC')

                    # Index by id for O(1) recovery lookup within this batch.
                    by_id = {e['eventid']: e for e in events}
                    paired = set()

                    for event in events:
                        # Zabbix returns r_eventid as a string; '0' means
                        # "no recovery yet". Coerce to int so the truthy
                        # check actually works — '0' would otherwise be
                        # truthy and slip through as if it were a recovery.
                        try:
                            recovery_id = int(event.get('r_eventid') or 0)
                        except (TypeError, ValueError):
                            recovery_id = 0

                        if recovery_id:
                            recovery_key = str(recovery_id)

                            # Avoid double-processing the same pair
                            pair_key = tuple(sorted((event['eventid'], recovery_key)))
                            if pair_key in paired:
                                continue

                            # Try to find the recovery in the current batch first.
                            recovery_event = by_id.get(recovery_key)
                            if recovery_event is None:
                                # Not in the 15 most recent — fetch by id.
                                try:
                                    fetched = api.event.get(eventids=[recovery_key], output=['eventid', 'clock'])
                                except Exception:
                                    logger.exception('Failed to fetch recovery event %s from server %s', recovery_key, assignment.zabbixserver)
                                    fetched = None
                                recovery_event = fetched[0] if fetched else None

                            if recovery_event is None:
                                # Skip pairs whose recovery we can't resolve.
                                continue

                            # Compute duration; skip if the clocks are bogus.
                            try:
                                start = int(event['clock'])
                                end = int(recovery_event['clock'])
                                duration = max(0, end - start)
                            except (KeyError, ValueError, TypeError):
                                continue

                            event_list.append(_event_row(assignment, event, end_time=recovery_event.get('clock'), duration=duration))
                            paired.add(pair_key)

                        else:
                            # Event is still open (no recovery yet), so there
                            # is no end_time and no duration.
                            event_list.append(_event_row(assignment, event, end_time=None, duration=None))
            except Exception:
                logger.exception('Failed to fetch Zabbix events for host %s on server %s', assignment.hostid, assignment.zabbixserver)
                fetch_errors.append(assignment.zabbixserver)

        context['table'] = ZabbixEventTable(event_list)
        context['fetch_errors'] = fetch_errors
        return context
