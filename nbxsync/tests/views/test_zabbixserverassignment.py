from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from virtualization.models import VirtualMachine

from dcim.models import Device
from utilities.testing import ViewTestCases, create_test_device, create_test_virtualmachine

from nbxsync.forms import ZabbixServerAssignmentForm
from nbxsync.models import ZabbixServer, ZabbixServerAssignment


class ZabbixServerAssignmentTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ZabbixServerAssignment

    @classmethod
    def setUpTestData(cls):
        cls.zabbix_servers = [
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
            ZabbixServer(
                name='Zabbix Server Bulk 3',
                description='Test Bulk Server 3',
                url='http://examplebulk3.com',
                token='bulk3-token',
                validate_certs=True,
            ),
        ]
        ZabbixServer.objects.bulk_create(cls.zabbix_servers)

        cls.devices = [
            create_test_device(name='ZabbixServer Assignment Test Device 1'),
            create_test_device(name='ZabbixServer Assignment Test Device 2'),
            create_test_device(name='ZabbixServer Assignment Test Device 3'),
            create_test_device(name='ZabbixServer Assignment Test Device 4'),
        ]
        cls.virtualmachines = [create_test_virtualmachine(name='VM1')]

        cls.device_ct = ContentType.objects.get_for_model(Device)
        cls.virtualmachine_ct = ContentType.objects.get_for_model(VirtualMachine)

        zabbix_serverassignments = [
            ZabbixServerAssignment(
                zabbixserver=cls.zabbix_servers[0],
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[0].id,
            ),
            ZabbixServerAssignment(
                zabbixserver=cls.zabbix_servers[1],
                assigned_object_type=cls.virtualmachine_ct,
                assigned_object_id=cls.virtualmachines[0].id,
            ),
        ]
        ZabbixServerAssignment.objects.bulk_create(zabbix_serverassignments)

        cls.form_data = {'zabbixserver': cls.zabbix_servers[1].id, 'device': cls.devices[1].id}

        cls.bulk_edit_data = {
            'zabbixserver': cls.zabbix_servers[2].id,
        }

    def test_serverassignment_form_prefills_assigned_object(self):
        self.user.is_superuser = True
        self.user.save()

        url = reverse('plugins:nbxsync:zabbixserverassignment_add')
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

    def test_serverassignment_form_invalid_content_type_triggers_prefill_exception(self):
        self.user.is_superuser = True
        self.user.save()

        # Use a clearly invalid content type ID
        invalid_ct_id = 99999  # unlikely to exist
        invalid_obj_id = 12345

        with self.assertLogs('nbxsync.forms', level='DEBUG') as cm:
            url = reverse('plugins:nbxsync:zabbixserverassignment_add')
            response = self.client.get(
                url,
                {'assigned_object_type': invalid_ct_id, 'assigned_object_id': invalid_obj_id},
            )
            self.assertEqual(response.status_code, 200)

        # Verify our except path executed and logged
        self.assertTrue(any('Prefill error' in msg for msg in cm.output))

    def test_clean_raises_if_multiple_assignments(self):
        form = ZabbixServerAssignmentForm(
            data={
                'device': self.devices[0].pk,
                'virtualmachine': self.virtualmachines[0].pk,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('virtualmachine', form.errors)
        self.assertIn('A ZabbixServer can only be assigned to a single object.', form.errors['virtualmachine'][0])

    def test_clean_sets_assigned_object_none_if_unassigned(self):
        form = ZabbixServerAssignmentForm(data={'zabbixserver': str(self.zabbix_servers[0].id)})

        form.is_valid()

        # Should not raise and assigned_object should be None
        self.assertIsNone(form.instance.assigned_object)

    def _get_base_url(self):
        return 'plugins:nbxsync:zabbixserverassignment_{}'
