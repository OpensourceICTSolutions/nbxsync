from unittest import TestCase
from unittest.mock import MagicMock, patch

from nbxsync.jobs.syncproxygroup import SyncProxyGroupJob
from nbxsync.utils.sync import ProxyGroupSync


class SyncProxyGroupJobTestCase(TestCase):
    @patch('nbxsync.jobs.syncproxygroup.safe_sync')
    def test_run_calls_safe_sync(self, mock_safe_sync):
        instance = MagicMock()
        job = SyncProxyGroupJob(instance=instance)

        job.run()

        mock_safe_sync.assert_called_once_with(ProxyGroupSync, instance)

    @patch('nbxsync.jobs.syncproxygroup.safe_sync')
    def test_run_raises_runtimeerror_on_exception(self, mock_safe_sync):
        instance = MagicMock()
        mock_safe_sync.side_effect = ValueError('some error')

        job = SyncProxyGroupJob(instance=instance)

        with self.assertRaises(RuntimeError) as ctx:
            job.run()

        self.assertIn('Unexpected error: some error', str(ctx.exception))
