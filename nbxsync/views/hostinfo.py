from django.http import Http404
from django.utils.translation import gettext as _
from django.views.generic import TemplateView
from django.contrib.contenttypes.models import ContentType

from nbxsync.utils import ZabbixConnection
from nbxsync.models import ZabbixServerAssignment
from nbxsync.tables import ZabbixProblemTable, ZabbixEventTable
from nbxsync.constants import OBJECT_TYPE_MODEL_MAP


class ZabbixHostProblemsView(TemplateView):
    template_name = 'nbxsync/modals/op_view.html'

    def get_context_data(self, objtype, pk, **kwargs):
        context = super().get_context_data(**kwargs)
        model = OBJECT_TYPE_MODEL_MAP.get(objtype)
        if not model:
            raise Http404(_('Unsupported object type: %(objtype)s') % {'objtype': objtype})

        object_ct = ContentType.objects.get_for_model(model)
        zabbixserverassignments = ZabbixServerAssignment.objects.filter(assigned_object_type=object_ct, assigned_object_id=pk).select_related('assigned_object_type')

        problem_list = []
        for zabbixserverassignment in zabbixserverassignments:
            if not zabbixserverassignment.hostid:
                continue
            # Get the problems for this host
            try:
                with ZabbixConnection(zabbixserverassignment.zabbixserver) as api:
                    problems = api.problem.get(hostids=zabbixserverassignment.hostid, sortfield='eventid', sortorder='DESC')
                    for problem in problems:
                        problem_list.append({'zabbixserver': zabbixserverassignment.zabbixserver, 'severity': problem['severity'], 'clock': problem['clock'], 'problem': problem['name'], 'acknowledged': problem['acknowledged'], 'opdata': problem['opdata']})
            except Exception:
                pass

        context['table'] = ZabbixProblemTable(problem_list)
        return context


class ZabbixHostEventsView(TemplateView):
    template_name = 'nbxsync/modals/op_view.html'

    def get_context_data(self, objtype, pk, **kwargs):
        context = super().get_context_data(**kwargs)
        model = OBJECT_TYPE_MODEL_MAP.get(objtype)
        if not model:
            raise Http404(_('Unsupported object type: %(objtype)s') % {'objtype': objtype})

        object_ct = ContentType.objects.get_for_model(model)
        zabbixserverassignments = ZabbixServerAssignment.objects.filter(assigned_object_type=object_ct, assigned_object_id=pk).select_related('assigned_object_type')

        event_list = []
        for zabbixserverassignment in zabbixserverassignments:
            if not zabbixserverassignment.hostid:
                continue
            # Get the events for this host
            try:
                with ZabbixConnection(zabbixserverassignment.zabbixserver) as api:
                    events = api.event.get(hostids=zabbixserverassignment.hostid, limit=15, sortfield=['clock', 'eventid'], sortorder='DESC')

                    # Index by id for O(1) lookup
                    by_id = {e['eventid']: e for e in events}

                    event_list = []
                    paired = set()

                    for event in events:
                        recovery_id = event.get('r_eventid', 0)

                        if recovery_id and recovery_id != 0:
                            # Avoid double-processing the same pair
                            pair_key = tuple(sorted((event['eventid'], recovery_id)))
                            if pair_key in paired:
                                continue

                            # Try to find the recovery in the current batch
                            recovery_event = by_id.get(recovery_id)
                            if not recovery_event:
                                # Not in the 15? Fetch it directly.
                                try:
                                    fetched = api.event.get(
                                        eventids=[recovery_id],
                                        output=['eventid', 'clock'],
                                    )
                                    recovery_event = fetched[0] if fetched else None
                                except Exception:
                                    recovery_event = None

                            if not recovery_event:
                                # If we still can't find the recovery, skip this pair
                                continue

                            # Compute duration (guard against weird clocks)
                            try:
                                start = int(event['clock'])
                                end = int(recovery_event['clock'])
                                duration = max(0, end - start)
                            except (KeyError, ValueError, TypeError):
                                continue

                            event_list.append(
                                {
                                    'zabbixserver': zabbixserverassignment.zabbixserver,
                                    'acknowledged': event.get('acknowledged', '0'),
                                    'duration': duration,
                                    'event': event.get('name'),
                                    'severity': event.get('severity'),
                                    'start_time': event['clock'],
                                    'end_time': recovery_event['clock'],
                                    'opdata': event['opdata'],
                                }
                            )
                            paired.add(pair_key)

                        else:
                            # Optional: include ongoing/non-recovered events with no duration
                            event_list.append(
                                {
                                    'zabbixserver': zabbixserverassignment.zabbixserver,
                                    'acknowledged': event.get('acknowledged', '0'),
                                    'duration': None,  # still open
                                    'event': event.get('name'),
                                    'severity': event.get('severity'),
                                    'start_time': event['clock'],
                                    'end_time': recovery_event['clock'],
                                    'opdata': event['opdata'],
                                }
                            )
            except Exception:
                pass

        context['table'] = ZabbixEventTable(event_list)
        return context
