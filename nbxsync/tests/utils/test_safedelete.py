from unittest import TestCase
from unittest.mock import MagicMock, patch

from nbxsync.utils.sync.safe_delete import safe_delete


class DummySync:
    __name__ = 'DummySync'


class SafeDeleteTests(TestCase):
    @patch('nbxsync.utils.sync.safe_delete.run_zabbix_operation')
    def test_safe_delete_success(self, mock_run_op):
        mock_obj = MagicMock()
        mock_result = MagicMock()
        mock_run_op.return_value = mock_result

        result = safe_delete(DummySync, mock_obj, extra_args={'id': 123})

        mock_run_op.assert_called_once_with(DummySync, mock_obj, 'delete', {'id': 123})
        self.assertEqual(result, mock_result)

    @patch('nbxsync.utils.sync.safe_delete.run_zabbix_operation', side_effect=ValueError('fail'))
    def test_safe_delete_raises_wrapped_runtime_error(self, mock_run_op):
        mock_obj = MagicMock()

        with self.assertRaises(RuntimeError) as cm:
            safe_delete(DummySync, mock_obj)

        self.assertIn('Error deleting DummySync: fail', str(cm.exception))
