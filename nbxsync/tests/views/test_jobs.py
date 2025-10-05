from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from utilities.testing import create_test_device, create_test_user

from nbxsync.choices import HostInterfaceRequirementChoices, ZabbixProxyTypeChoices
from nbxsync.models import ZabbixProxy, ZabbixProxyGroup, ZabbixServer, ZabbixTemplate


class TriggerSyncJobViewTestCase(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)

        self.device = create_test_device(name='TestDevice')
        self.zabbixserver = ZabbixServer.objects.create(
            name='Zabbix Server A',
            description='Test Server',
            url='http://example.com',
            token='dummy-token',
            validate_certs=True,
        )
        self.proxygroup = ZabbixProxyGroup.objects.create(
            name='Proxy Test Group A',
            zabbixserver=self.zabbixserver,
            description='ProxyGroup',
            failover_delay='1m',
            min_online=1,
        )
        self.proxy = ZabbixProxy.objects.create(
            name='Active Proxy #1',
            zabbixserver=self.zabbixserver,
            proxygroup=self.proxygroup,
            local_address='192.168.1.1',
            operating_mode=ZabbixProxyTypeChoices.ACTIVE,
        )
        self.template = ZabbixTemplate.objects.create(
            name='Template #1',
            zabbixserver=self.zabbixserver,
            templateid=1,
            interface_requirements=[HostInterfaceRequirementChoices.AGENT, HostInterfaceRequirementChoices.ANY],
        )

    def _run_sync_view_test(self, urlname, kwargs, expected_obj, job_func, message_snippet, expected_return=204):
        url = reverse(f'plugins:nbxsync:{urlname}', kwargs=kwargs)
        with patch('nbxsync.views.jobs.get_queue') as mock_get_queue:
            mock_queue = mock_get_queue.return_value
            mock_job = mock_queue.create_job.return_value
            mock_queue.enqueue_job.return_value = None

            response = self.client.get(url)

            self.assertEqual(response.status_code, expected_return)

            mock_queue.create_job.assert_called_once_with(func=job_func, args=[expected_obj], timeout=9000)
            mock_queue.enqueue_job.assert_called_once_with(mock_job)

            messages = list(get_messages(response.wsgi_request))
            self.assertTrue(any(message_snippet in str(m.message) for m in messages))

    def test_enqueue_host_sync_job(self):
        self._run_sync_view_test(
            urlname='zabbixhost_sync',
            kwargs={'objtype': 'device', 'pk': self.device.pk},
            expected_obj=self.device,
            job_func='nbxsync.worker.synchost',
            message_snippet='Sync job enqueued',
        )

    def test_invalid_host_objtype_raises_404(self):
        url = reverse('plugins:nbxsync:zabbixhost_sync', kwargs={'objtype': 'INVALID', 'pk': 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_enqueue_proxygroup_sync_job(self):
        self._run_sync_view_test(
            urlname='zabbixproxygroup_sync',
            kwargs={'pk': self.proxygroup.pk},
            expected_obj=self.proxygroup,
            job_func='nbxsync.worker.syncproxygroup',
            message_snippet='Proxygroup sync job enqueued for',
        )

    def test_enqueue_proxy_sync_job(self):
        self._run_sync_view_test(
            urlname='zabbixproxy_sync',
            kwargs={'pk': self.proxy.pk},
            expected_obj=self.proxy,
            job_func='nbxsync.worker.syncproxy',
            message_snippet='Proxy sync job enqueued for',
        )

    def test_enqueue_template_sync_job(self):
        self._run_sync_view_test(urlname='zabbixserver_templatessync', kwargs={'pk': self.zabbixserver.pk}, expected_obj=self.zabbixserver, job_func='nbxsync.worker.synctemplates', message_snippet='Template sync job enqueued for templates on', expected_return=302)

    def test_sync_info_modal_for_device(self):
        url = reverse(
            'plugins:nbxsync:zabbixhost_info',
            kwargs={
                'objtype': 'device',
                'pk': self.device.pk,
            },
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'nbxsync/modals/sync_info.html')
        self.assertContains(response, 'missing one or more of the following')
