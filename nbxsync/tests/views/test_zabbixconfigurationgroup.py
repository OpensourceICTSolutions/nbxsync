from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory

from utilities.testing import ViewTestCases, create_test_user, create_test_device
from ipam.models import IPAddress
from dcim.models import Device

from nbxsync.models import ZabbixServer, ZabbixConfigurationGroup, ZabbixHostInterface, ZabbixConfigurationGroupAssignment, ZabbixServerAssignment
from nbxsync.tables import ZabbixConfigurationGroupTable, ZabbixHostInterfaceObjectViewTable, ZabbixConfigurationGroupAssignmentDetailViewTable, ZabbixServerAssignmentObjectViewTable
from nbxsync.views import ZabbixConfigurationGroupView


class ZabbixConfigurationGroupViewTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ZabbixConfigurationGroup
    table = ZabbixConfigurationGroupTable

    @classmethod
    def setUpTestData(cls):
        # Create a couple of groups
        ZabbixConfigurationGroup.objects.bulk_create(
            [
                ZabbixConfigurationGroup(name='Baseline Config', description='Default baseline'),
                ZabbixConfigurationGroup(name='Hardening Config', description='Hardened config set'),
            ]
        )

        cls.devices = [
            create_test_device(name='ConfigGroup Test Device 1'),
            create_test_device(name='ConfigGroup Test Device 2'),
            create_test_device(name='ConfigGroup Test Device 3'),
            create_test_device(name='ConfigGroup Test Device 4'),
        ]

        cls.zabbix_servers = [
            ZabbixServer.objects.create(
                name='Zabbix Server Bulk 1',
                description='Test Bulk Server 1',
                url='http://examplebulk1.com',
                token='bulk1-token',
                validate_certs=True,
            ),
        ]
        cls.ipaddresses = [IPAddress.objects.create(address='1.1.1.1/32')]

        cls.form_data = {
            'name': 'Telemetry Config',
            'description': 'Collect and forward metrics',
        }

        cls.bulk_edit_data = {
            'description': 'Updated in bulk',
        }

    def _get_base_url(self):
        return 'plugins:nbxsync:zabbixconfigurationgroup_{}'

    def test_get_extra_context_builds_and_configures_tables_with_objects(self):
        """
        When there are HostInterface and Assignment objects referring to this ConfigurationGroup,
        the view should return real, configured tables with rows.
        """
        # Superuser for table.configure()
        user = create_test_user(username='zbxcfg superuser')
        user.is_superuser = True
        user.save()

        factory = RequestFactory()

        # Use an existing configuration group
        cfg = ZabbixConfigurationGroup.objects.first()
        self.assertIsNotNone(cfg, 'Expected at least one ZabbixConfigurationGroup in DB')

        # ContentType for the instance's model (the view queries HostInterface/ServerAssignment by this)
        cfg_ct = ContentType.objects.get_for_model(ZabbixConfigurationGroup)
        device_ct = ContentType.objects.get_for_model(Device)

        # Create a HostInterface assigned to this config group instance
        ZabbixHostInterface.objects.create(
            zabbixserver=self.zabbix_servers[0],
            type=1,
            useip=1,
            interface_type=1,
            ip=self.ipaddresses[0],
            port=10051,
            assigned_object_type=cfg_ct,
            assigned_object_id=cfg.pk,
        )

        # Create a ConfigurationGroupAssignment pointing to this config group
        ZabbixConfigurationGroupAssignment.objects.create(
            zabbixconfigurationgroup=cfg,
            assigned_object_type=device_ct,
            assigned_object_id=self.devices[0].pk,
        )

        # Create a ZabbixServerAssignment pointing to this config group
        ZabbixServerAssignment.objects.create(
            zabbixserver=self.zabbix_servers[0],
            assigned_object_type=cfg_ct,
            assigned_object_id=cfg.pk,
        )

        request = factory.get('/dummy')
        request.user = user

        view = ZabbixConfigurationGroupView()
        context = view.get_extra_context(request, cfg)

        hi_table = context.get('hostinterface_assignment_table')
        asn_table = context.get('objectassignments_table')
        srv_table = context.get('zabbixserver_assignments_table')

        # All tables are present and of the right type
        self.assertIsNotNone(hi_table)
        self.assertIsInstance(hi_table, ZabbixHostInterfaceObjectViewTable)

        self.assertIsNotNone(asn_table)
        self.assertIsInstance(asn_table, ZabbixConfigurationGroupAssignmentDetailViewTable)

        self.assertIsNotNone(srv_table)
        self.assertIsInstance(srv_table, ZabbixServerAssignmentObjectViewTable)

        # Ensure tables were built from non-empty querysets
        self.assertGreater(len(list(hi_table.rows)), 0)
        self.assertGreater(len(list(asn_table.rows)), 0)
        self.assertGreater(len(list(srv_table.rows)), 0)

    def test_get_extra_context_returns_none_tables_when_no_objects(self):
        """
        When there are no related HostInterface or Assignment objects, the view should
        return None for both tables.
        """
        # Superuser for table.configure() (even though not used here)
        user = create_test_user(username='zbxcfg superuser no objects')
        user.is_superuser = True
        user.save()

        factory = RequestFactory()

        # Use an existing configuration group
        cfg = ZabbixConfigurationGroup.objects.last()
        self.assertIsNotNone(cfg, 'Expected at least one ZabbixConfigurationGroup in DB')

        request = factory.get('/dummy')
        request.user = user

        view = ZabbixConfigurationGroupView()
        context = view.get_extra_context(request, cfg)

        self.assertIsNone(context.get('hostinterface_assignment_table'))
        self.assertIsNone(context.get('objectassignments_table'))
        self.assertIsNone(context.get('zabbixserver_assignments_table'))

    def test_get_extra_context_merges_object_assignments_from_utility(self):
        """
        get_extra_context() should merge the dict returned by
        nbxsync.utils.inheritance.get_zabbixassignments_for_request into the context.
        """
        user = create_test_user(username='zbxcfg merge user')
        user.is_superuser = True
        user.save()

        factory = RequestFactory()
        cfg = ZabbixConfigurationGroup.objects.first()

        request = factory.get('/dummy')
        request.user = user

        mocked_assignments = {'some_extra': 'value', 'another_key': 123}

        target = f'{ZabbixConfigurationGroupView.__module__}.get_zabbixassignments_for_request'
        with patch(target, return_value=mocked_assignments) as mocked_fn:
            view = ZabbixConfigurationGroupView()
            context = view.get_extra_context(request, cfg)

            mocked_fn.assert_called_once_with(cfg, request)

        # Keys from the mocked dict should be present in the final context
        for k, v in mocked_assignments.items():
            self.assertIn(k, context)
            self.assertEqual(context[k], v)
