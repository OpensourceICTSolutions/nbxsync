from unittest import TestCase
from unittest.mock import MagicMock, patch

from nbxsync.jobs.syncproxy import SyncProxyJob
from nbxsync.utils.sync import ProxyGroupSync, ProxySync


class SyncProxyJobTestCase(TestCase):
    @patch('nbxsync.jobs.syncproxy.safe_sync')
    def test_run_with_proxygroup(self, mock_safe_sync):
        proxygroup = MagicMock()
        instance = MagicMock()
        instance.proxygroup = proxygroup

        job = SyncProxyJob(instance=instance)
        job.run()

        mock_safe_sync.assert_any_call(ProxyGroupSync, proxygroup)
        mock_safe_sync.assert_any_call(ProxySync, instance)
        self.assertEqual(mock_safe_sync.call_count, 2)

    @patch('nbxsync.jobs.syncproxy.safe_sync')
    def test_run_without_proxygroup(self, mock_safe_sync):
        instance = MagicMock()
        instance.proxygroup = None

        job = SyncProxyJob(instance=instance)
        job.run()

        mock_safe_sync.assert_called_once_with(ProxySync, instance)

    @patch('nbxsync.jobs.syncproxy.safe_sync')
    def test_run_raises_runtimeerror_on_failure(self, mock_safe_sync):
        instance = MagicMock()
        instance.proxygroup = None
        mock_safe_sync.side_effect = ValueError('unexpected!')

        job = SyncProxyJob(instance=instance)

        with self.assertRaises(RuntimeError) as ctx:
            job.run()

        self.assertIn('Unexpected error: unexpected!', str(ctx.exception))
