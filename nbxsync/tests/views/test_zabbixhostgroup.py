from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory

from dcim.models import Device
from utilities.testing import ViewTestCases, create_test_device, create_test_user


from nbxsync.models import ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixServer
from nbxsync.views import ZabbixHostgroupView
from nbxsync.tables import ZabbixHostgroupObjectViewTable


class ZabbixHostgroupTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ZabbixHostgroup

    @classmethod
    def setUpTestData(cls):
        zabbix_servers = [
            ZabbixServer(
                name='Zabbix Server Bulk 1',
                description='Test Bulk Server 1',
                url='http://examplebulk1.com',
                token='bulk1-token',
                validate_certs=True,
            ),
            ZabbixServer(
                name='Zabbix Server Bulk 2',
                description='Test Bulk Server 2',
                url='http://examplebulk2.com',
                token='bulk2-token',
                validate_certs=True,
            ),
        ]
        ZabbixServer.objects.bulk_create(zabbix_servers)

        zabbix_hostgroups = [
            ZabbixHostgroup(
                name='Zabbix Hostgroup Bulk 1',
                groupid=1,
                description='Bulk Created #1',
                value='Demo',
                zabbixserver=zabbix_servers[0],
            ),
            ZabbixHostgroup(
                name='Zabbix Hostgroup Bulk 2',
                groupid=1,
                description='Bulk Created #2',
                value='Demo',
                zabbixserver=zabbix_servers[1],
            ),
        ]
        ZabbixHostgroup.objects.bulk_create(zabbix_hostgroups)

        cls.form_data = {
            'name': 'Zabbix Hostgroup 3',
            'description': 'Bulk Description',
            'value': 'Bulk Value',
            'groupid': 2,
            'zabbixserver': zabbix_servers[0].id,
        }

        cls.bulk_edit_data = {
            'description': 'Bulk Hostgroup',
        }

    def _get_base_url(self):
        return 'plugins:nbxsync:zabbixhostgroup_{}'

    def test_get_extra_context_builds_and_configures_real_table(self):
        # Setup a superuser
        user = create_test_user(username='zbxhostgroup user')
        user.is_superuser = True
        user.save()

        factory = RequestFactory()

        # Create a real device
        device = create_test_device(name='Hostgroup Test Device 1')
        device_ct = ContentType.objects.get_for_model(Device)

        # Use an actual existing hostgroup, as this is setup in the setUpTestData phase
        zabbix_hostgroup = ZabbixHostgroup.objects.first()
        self.assertIsNotNone(zabbix_hostgroup, 'Expected at least one ZabbixHostgroup in DB')

        # Create the assignment
        ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=zabbix_hostgroup,
            assigned_object_type=device_ct,
            assigned_object_id=device.id,
        )

        request = factory.get('/dummy')
        request.user = user
        view = ZabbixHostgroupView()
        context = view.get_extra_context(request, zabbix_hostgroup)

        table = context.get('hostgroupassignment_table')
        self.assertIsNotNone(table)
        self.assertIsInstance(table, ZabbixHostgroupObjectViewTable)

        # Ensure table was built from a non-empty queryset
        self.assertGreater(len(list(table.rows)), 0)

    def test_get_extra_context_builds_and_configures_real_table_with_no_objects(self):
        # Setup a superuser
        user = create_test_user(username='zbxhostgroup user')
        user.is_superuser = True
        user.save()

        factory = RequestFactory()

        # Use an actual existing hostgroup, as this is setup in the setUpTestData phase
        zabbix_hostgroup = ZabbixHostgroup.objects.first()
        self.assertIsNotNone(zabbix_hostgroup, 'Expected at least one ZabbixHostgroup in DB')

        request = factory.get('/dummy')
        request.user = user
        view = ZabbixHostgroupView()
        context = view.get_extra_context(request, zabbix_hostgroup)

        table = context.get('hostgroupassignment_table')
        self.assertIsNone(table)
