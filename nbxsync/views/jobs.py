from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView
from django_rq import get_queue


from nbxsync.models import ZabbixMaintenance, ZabbixProxy, ZabbixProxyGroup, ZabbixServer
from nbxsync.constants import OBJECT_TYPE_MODEL_MAP

__all__ = (
    'ZabbixSyncInfoModalView',
    'TriggerHostSyncJobView',
    'TriggerProxySyncJobView',
    'TriggerTemplateSyncJobView',
    'TriggerProxyGroupSyncJobView',
    'TriggerMaintenanceSyncJobView',
)


class ZabbixSyncInfoModalView(TemplateView):
    template_name = 'nbxsync/modals/sync_info.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['missing_requirements'] = _('This host is missing one or more of the following: Zabbix Server Assignment, Zabbix Host Interface, Zabbix Hostgroup. Please configure these before syncing.')
        return context


class TriggerHostSyncJobView(View):
    def get(self, request, objtype, pk):
        model = OBJECT_TYPE_MODEL_MAP.get(objtype)
        if not model:
            raise Http404(_('Unsupported object type: %(objtype)s') % {'objtype': objtype})

        instance = get_object_or_404(model, pk=pk)
        messages.success(request, _('Sync job enqueued for %(name)s') % {'name': str(instance)})
        queue = get_queue('low')
        queue.enqueue_job(
            queue.create_job(
                func='nbxsync.worker.synchost',
                args=[instance],
                timeout=9000,
            )
        )

        target = request.headers.get('HX-Current-URL') or request.META.get('HTTP_REFERER') or instance.get_absolute_url()
        resp = HttpResponse(status=204)
        resp['HX-Redirect'] = target
        return resp


class TriggerProxyGroupSyncJobView(View):
    def get(self, request, pk):
        instance = get_object_or_404(ZabbixProxyGroup, pk=pk)
        queue = get_queue('low')
        queue.enqueue_job(
            queue.create_job(
                func='nbxsync.worker.syncproxygroup',
                args=[instance],
                timeout=9000,
            )
        )
        messages.success(request, _('Proxygroup sync job enqueued for %(name)s') % {'name': str(instance)})
        target = request.headers.get('HX-Current-URL') or request.META.get('HTTP_REFERER') or instance.get_absolute_url()
        resp = HttpResponse(status=204)
        resp['HX-Redirect'] = target
        return resp


class TriggerProxySyncJobView(View):
    def get(self, request, pk):
        instance = get_object_or_404(ZabbixProxy, pk=pk)
        queue = get_queue('low')
        queue.enqueue_job(
            queue.create_job(
                func='nbxsync.worker.syncproxy',
                args=[instance],
                timeout=9000,
            )
        )

        messages.success(request, _('Proxy sync job enqueued for %(name)s') % {'name': str(instance)})
        target = request.headers.get('HX-Current-URL') or request.META.get('HTTP_REFERER') or instance.get_absolute_url()
        resp = HttpResponse(status=204)
        resp['HX-Redirect'] = target
        return resp


class TriggerTemplateSyncJobView(View):
    def get(self, request, pk):
        zabbixserver = get_object_or_404(ZabbixServer, pk=pk)
        queue = get_queue('low')
        queue.enqueue_job(
            queue.create_job(
                func='nbxsync.worker.synctemplates',
                args=[zabbixserver],
                timeout=9000,
            )
        )
        messages.success(request, _('Template sync job enqueued for templates on %(name)s') % {'name': str(zabbixserver)})
        return redirect(zabbixserver.get_absolute_url())


class TriggerMaintenanceSyncJobView(View):
    def get(self, request, pk):
        instance = get_object_or_404(ZabbixMaintenance, pk=pk)
        queue = get_queue('low')
        queue.enqueue_job(
            queue.create_job(
                func='nbxsync.worker.syncmaintenance',
                args=[instance],
                timeout=9000,
            )
        )

        messages.success(request, _('Maintenance window sync job enqueued for %(name)s') % {'name': str(instance)})
        target = request.headers.get('HX-Current-URL') or request.META.get('HTTP_REFERER') or instance.get_absolute_url()
        resp = HttpResponse(status=204)
        resp['HX-Redirect'] = target
        return resp
