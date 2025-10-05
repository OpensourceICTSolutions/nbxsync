from unittest import TestCase
from unittest.mock import MagicMock, patch

from nbxsync.utils.sync.safe_sync import safe_sync


class DummySync:
    __name__ = 'DummySync'


class SafeSyncTests(TestCase):
    @patch('nbxsync.utils.sync.safe_sync.run_zabbix_operation')
    def test_safe_sync_success(self, mock_run_op):
        mock_obj = MagicMock()
        mock_result = MagicMock()
        mock_run_op.return_value = mock_result

        result = safe_sync(DummySync, mock_obj, extra_args={'foo': 'bar'})

        mock_run_op.assert_called_once_with(DummySync, mock_obj, 'sync', {'foo': 'bar'})
        self.assertEqual(result, mock_result)

    @patch('nbxsync.utils.sync.safe_sync.run_zabbix_operation', side_effect=ValueError('Oops'))
    def test_safe_sync_raises_wrapped_runtime_error(self, mock_run_op):
        mock_obj = MagicMock()

        with self.assertRaises(RuntimeError) as context:
            safe_sync(DummySync, mock_obj)

        self.assertIn('Error syncing DummySync: Oops', str(context.exception))
