from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from dcim.models import Device
from utilities.testing import ViewTestCases, create_test_device, create_test_virtualmachine

from nbxsync.forms import ZabbixHostgroupAssignmentForm
from nbxsync.models import ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixServer


class ZabbixHostgroupAssignmentTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ZabbixHostgroupAssignment

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

        cls.zabbix_hostgroups = [
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
            ZabbixHostgroup(
                name='Zabbix Hostgroup Bulk 3',
                groupid=3,
                description='Bulk Created #3',
                value='Demo',
                zabbixserver=zabbix_servers[1],
            ),
        ]
        ZabbixHostgroup.objects.bulk_create(cls.zabbix_hostgroups)

        cls.devices = [
            create_test_device(name='Hostgroup Test Device 1'),
            create_test_device(name='Hostgroup Test Device 2'),
            create_test_device(name='Hostgroup Test Device 3'),
        ]
        cls.virtualmachines = [create_test_virtualmachine(name='Hostgroup Test VM 1')]
        cls.device_ct = ContentType.objects.get_for_model(Device)

        zabbix_hostgroupassignments = [
            ZabbixHostgroupAssignment(
                zabbixhostgroup=cls.zabbix_hostgroups[0],
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[0].id,
            ),
            ZabbixHostgroupAssignment(
                zabbixhostgroup=cls.zabbix_hostgroups[1],
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[1].id,
            ),
        ]
        ZabbixHostgroupAssignment.objects.bulk_create(zabbix_hostgroupassignments)

        cls.form_data = {'zabbixhostgroup': cls.zabbix_hostgroups[0].pk, 'device': cls.devices[2].id}

        cls.bulk_edit_data = {'zabbixhostgroup': cls.zabbix_hostgroups[2].pk}

    def test_hostgroupassignment_form_prefills_assigned_object(self):
        self.user.is_superuser = True
        self.user.save()

        url = reverse('plugins:nbxsync:zabbixhostgroupassignment_add')
        response = self.client.get(
            url,
            {
                'assigned_object_type': self.device_ct.pk,
                'assigned_object_id': self.devices[0].pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.devices[0].name)

        # Check that form initial includes the device prefilled
        html = response.content.decode().replace('\n', '').replace('  ', '')
        expected = f'value="{self.devices[0].pk}" selected'
        self.assertIn(expected, html)

    def test_hostgroupassignment_form_invalid_content_type_triggers_prefill_exception(self):
        self.user.is_superuser = True
        self.user.save()

        # Use a clearly invalid content type ID
        invalid_ct_id = 99999  # unlikely to exist
        invalid_obj_id = 12345

        with self.assertLogs('nbxsync.forms', level='DEBUG') as cm:
            url = reverse('plugins:nbxsync:zabbixhostgroupassignment_add')
            response = self.client.get(
                url,
                {'assigned_object_type': invalid_ct_id, 'assigned_object_id': invalid_obj_id},
            )
            self.assertEqual(response.status_code, 200)

        # Verify our except path executed and logged
        self.assertTrue(any('Prefill error' in msg for msg in cm.output))

    def test_clean_raises_if_multiple_assignments(self):
        form = ZabbixHostgroupAssignmentForm(
            data={
                'device': self.devices[0].pk,
                'virtualmachine': self.virtualmachines[0].pk,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('virtualmachine', form.errors)
        self.assertIn('A Hostgroup can only be assigned to a single object.', form.errors['virtualmachine'][0])

    def test_clean_sets_assigned_object_none_if_unassigned(self):
        form = ZabbixHostgroupAssignmentForm(data={'zabbixhostgroup': str(self.zabbix_hostgroups[0].id)})

        form.is_valid()

        # Should not raise and assigned_object should be None
        self.assertIsNone(form.instance.assigned_object)

    def _get_base_url(self):
        return 'plugins:nbxsync:zabbixhostgroupassignment_{}'
