from unittest.mock import MagicMock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from virtualization.models import VirtualMachine

from dcim.models import Device, Site, SiteGroup
from utilities.testing import create_test_device

from nbxsync.models import ZabbixConfigurationGroup, ZabbixServer, ZabbixServerAssignment
from nbxsync.systemjobs.sync_objects import SyncObjectsJob


class SyncObjectsSystemJobTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix Server 1', url='http://zabbix1.local', token='token1')
        cls.device1 = create_test_device(name='SyncObjects Dev 1')
        cls.device2 = create_test_device(name='SyncObjects Dev 2')
        cls.device_ct = ContentType.objects.get_for_model(Device)
        cls.cfg_ct = ContentType.objects.get_for_model(ZabbixConfigurationGroup)
        cls.site_ct = ContentType.objects.get_for_model(Site)
        cls.sitegroup_ct = ContentType.objects.get_for_model(SiteGroup)
        cls.vm_ct = ContentType.objects.get_for_model(VirtualMachine)

    def setUp(self):
        self.job_active_patcher = patch('nbxsync.systemjobs.sync_objects._job_is_active', return_value=False)
        self.mock_job_is_active = self.job_active_patcher.start()
        self.addCleanup(self.job_active_patcher.stop)

    @staticmethod
    def _ref(instance):
        content_type = ContentType.objects.get_for_model(instance)
        return (content_type.app_label, content_type.model, instance.pk)

    @staticmethod
    def _enqueued_refs(queue):
        return [tuple(call.kwargs['args']) for call in queue.create_job.call_args_list]

    @patch('nbxsync.systemjobs.sync_objects.get_queue')
    def test_run_enqueues_job_for_each_device(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.device1.pk)
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.device2.pk)

        job = SyncObjectsJob(job=MagicMock())
        job.run()

        self.assertEqual(queue.create_job.call_count, 2)
        self.assertEqual(queue.enqueue_job.call_count, 2)

        enqueued_refs = self._enqueued_refs(queue)
        self.assertIn(self._ref(self.device1), enqueued_refs)
        self.assertIn(self._ref(self.device2), enqueued_refs)

    @patch('nbxsync.systemjobs.sync_objects.get_queue')
    def test_run_passes_correct_args_to_create_job(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.device1.pk)

        job = SyncObjectsJob(job=MagicMock())
        job.run()

        _, kwargs = queue.create_job.call_args
        self.assertEqual(kwargs.get('func'), 'nbxsync.worker.synchost')
        self.assertEqual(kwargs.get('timeout'), 9000)
        self.assertEqual(tuple(kwargs.get('args')), self._ref(self.device1))
        self.assertEqual(kwargs.get('job_id'), f'nbxsync-host-dcim-device-{self.device1.pk}')

    @patch('nbxsync.systemjobs.sync_objects.get_queue')
    def test_run_skips_configurationgroup_assignments(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue

        cfg = ZabbixConfigurationGroup.objects.create(name='Test CFG', description='')
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.cfg_ct, assigned_object_id=cfg.pk)

        job = SyncObjectsJob(job=MagicMock())
        job.run()

        mock_get_queue.assert_not_called()

    @patch('nbxsync.systemjobs.sync_objects.get_queue')
    def test_run_enqueues_devices_for_sitegroup_assignment(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue
        sitegroup = SiteGroup.objects.create(name='CH', slug='ch')
        site = Site.objects.create(name='CH-STA', slug='ch-sta', group=sitegroup)
        device = create_test_device(name='Dev-at-CH-STA', site=site)
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.sitegroup_ct, assigned_object_id=sitegroup.pk)
        job = SyncObjectsJob(job=MagicMock())
        job.run()
        enqueued_refs = self._enqueued_refs(queue)
        self.assertIn(self._ref(device), enqueued_refs)

    @patch('nbxsync.systemjobs.sync_objects.get_queue')
    def test_run_enqueues_vms_for_sitegroup_assignment(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue
        sitegroup = SiteGroup.objects.create(name='CH', slug='ch')
        site = Site.objects.create(name='CH-STA', slug='ch-sta', group=sitegroup)
        vm = VirtualMachine.objects.create(name='VM-at-CH-STA', site=site)
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.sitegroup_ct, assigned_object_id=sitegroup.pk)
        job = SyncObjectsJob(job=MagicMock())
        job.run()
        enqueued_refs = self._enqueued_refs(queue)
        self.assertIn(self._ref(vm), enqueued_refs)

    @patch('nbxsync.systemjobs.sync_objects.get_queue')
    def test_run_continues_on_duplicate_device(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue
        server2 = ZabbixServer.objects.create(name='Zabbix Server 2', url='http://zabbix2.local', token='token2')
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.device1.pk)
        ZabbixServerAssignment.objects.create(zabbixserver=server2, assigned_object_type=self.device_ct, assigned_object_id=self.device1.pk)
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.device2.pk)
        job = SyncObjectsJob(job=MagicMock())
        job.run()
        self.assertEqual(queue.create_job.call_count, 2)
        enqueued_refs = self._enqueued_refs(queue)
        self.assertIn(self._ref(self.device1), enqueued_refs)
        self.assertIn(self._ref(self.device2), enqueued_refs)

    @patch('nbxsync.systemjobs.sync_objects.get_queue')
    def test_run_enqueues_devices_for_site_assignment(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue
        site = Site.objects.create(name='Site-Test', slug='site-test')
        device = create_test_device(name='Dev-at-Site-Test', site=site)
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.site_ct, assigned_object_id=site.pk)
        job = SyncObjectsJob(job=MagicMock())
        job.run()
        enqueued_refs = self._enqueued_refs(queue)
        self.assertIn(self._ref(device), enqueued_refs)

    @patch('nbxsync.systemjobs.sync_objects.get_queue')
    def test_run_skips_disabled_assignment(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.device1.pk)
        server2 = ZabbixServer.objects.create(name='Zabbix Server 2', url='http://zabbix2.local', token='token2')
        ZabbixServerAssignment.objects.create(zabbixserver=server2, assigned_object_type=self.device_ct, assigned_object_id=self.device2.pk, sync_enabled=False)
        job = SyncObjectsJob(job=MagicMock())
        job.run()
        self.assertEqual(queue.create_job.call_count, 1)
        enqueued_refs = self._enqueued_refs(queue)
        self.assertIn(self._ref(self.device1), enqueued_refs)

    @patch('nbxsync.systemjobs.sync_objects.get_queue')
    def test_run_skips_disabled_zabbixserver(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue
        server2 = ZabbixServer.objects.create(name='Zabbix Server 2', url='http://zabbix2.local', token='token2', sync_enabled=False)
        ZabbixServerAssignment.objects.create(zabbixserver=server2, assigned_object_type=self.device_ct, assigned_object_id=self.device1.pk)
        job = SyncObjectsJob(job=MagicMock())
        job.run()
        mock_get_queue.assert_not_called()

    @patch('nbxsync.systemjobs.sync_objects.get_queue')
    def test_run_skips_job_already_queued_or_running(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue
        self.mock_job_is_active.return_value = True
        ZabbixServerAssignment.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device1.pk,
        )

        SyncObjectsJob(job=MagicMock()).run()

        self.mock_job_is_active.assert_called_once_with(queue, f'nbxsync-host-dcim-device-{self.device1.pk}')
        queue.create_job.assert_not_called()
        queue.enqueue_job.assert_not_called()

    @patch('nbxsync.systemjobs.sync_objects.get_queue')
    def test_run_handles_empty_sitegroup(self, mock_get_queue):
        queue = MagicMock()
        mock_get_queue.return_value = queue
        sitegroup = SiteGroup.objects.create(name='Empty', slug='empty')
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.sitegroup_ct, assigned_object_id=sitegroup.pk)
        job = SyncObjectsJob(job=MagicMock())
        job.run()
        mock_get_queue.assert_not_called()

    @patch('nbxsync.systemjobs.sync_objects.get_queue')
    def test_run_does_nothing_when_no_assignments_exist(self, mock_get_queue):
        job = SyncObjectsJob(job=MagicMock())
        job.run()

        mock_get_queue.assert_not_called()
