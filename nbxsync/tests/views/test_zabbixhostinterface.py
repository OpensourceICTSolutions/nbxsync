from django.urls import reverse
from django.contrib.contenttypes.models import ContentType

from utilities.testing import ModelViewTestCase, ViewTestCases, create_test_device, create_test_virtualmachine
from utilities.testing.utils import post_data
from ipam.models import IPAddress
from dcim.models import Device

from nbxsync.forms import ZabbixHostInterfaceForm
from nbxsync.models import ZabbixHostInterface, ZabbixServer, ZabbixServerAssignment


class ZabbixHostInterfaceAssignmentTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ModelViewTestCase,
):
    model = ZabbixHostInterface
    model_form_class = ZabbixHostInterfaceForm

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
        ]
        ZabbixServer.objects.bulk_create(cls.zabbix_servers)

        cls.devices = [
            create_test_device(name='Hostgroup Test Device 1'),
            create_test_device(name='Hostgroup Test Device 2'),
            create_test_device(name='Hostgroup Test Device 3'),
            create_test_device(name='Hostgroup Test Device 4'),
        ]
        cls.virtualmachines = [create_test_virtualmachine(name='VM1')]

        device_ct = ContentType.objects.get_for_model(Device)
        cls.ipaddresses = [
            IPAddress.objects.create(address='1.1.1.1/32'),
            IPAddress.objects.create(address='1.1.1.2/32'),
            IPAddress.objects.create(address='1.1.1.3/32'),
            IPAddress.objects.create(address='1.1.1.5/32'),
        ]

        zabbix_hostinterfaces = [
            ZabbixHostInterface(
                zabbixserver=cls.zabbix_servers[0],
                type=1,
                useip=1,
                interface_type=1,
                ip=cls.ipaddresses[0],
                port=10051,
                assigned_object_type=device_ct,
                assigned_object_id=cls.devices[0].id,
            ),
            ZabbixHostInterface(
                zabbixserver=cls.zabbix_servers[0],
                type=1,
                useip=1,
                interface_type=1,
                ip=cls.ipaddresses[1],
                port=10051,
                assigned_object_type=device_ct,
                assigned_object_id=cls.devices[1].id,
            ),
        ]
        ZabbixHostInterface.objects.bulk_create(zabbix_hostinterfaces)

        cls.form_data = {
            'zabbixserver': cls.zabbix_servers[0].pk,
            'type': 1,
            'useip': 1,
            'interface_type': 1,
            'ip': cls.ipaddresses[2].id,
            'port': 10051,
            'device': cls.devices[2].id,
        }

    def test_double_assignment(self):
        form_data = {
            'zabbixserver': self.zabbix_servers[0].pk,
            'type': 1,
            'useip': 1,
            'interface_type': 1,
            'ip': self.ipaddresses[3].pk,
            'port': 10051,
            'device': self.devices[3].pk,
            'virtualmachine': self.virtualmachines[0].pk,
        }

        # Make the user superuser so we dont have to worry about *any* permissions
        self.user.is_superuser = True
        self.user.save()

        # Try POST with model-level permission
        request = {
            'path': self._get_url('add'),
            'data': post_data(form_data),
        }
        post_response = self.client.post(**request)
        self.assertHttpStatus(post_response, 200)  # Expect HTTP/200, as its an error
        form = post_response.context['form']
        self.assertIn('An Host Interface can only be assigned to a single object.', str(form.errors))

    def test_inventory_form_invalid_content_type_triggers_prefill_exception(self):
        self.user.is_superuser = True
        self.user.save()

        # Use a clearly invalid content type ID
        invalid_ct_id = 99999  # unlikely to exist
        invalid_obj_id = 12345

        with self.assertLogs('nbxsync.forms', level='DEBUG') as cm:
            url = reverse('plugins:nbxsync:zabbixhostinterface_add')
            response = self.client.get(
                url,
                {'assigned_object_type': invalid_ct_id, 'assigned_object_id': invalid_obj_id},
            )
            self.assertEqual(response.status_code, 200)

        # Verify our except path executed and logged
        self.assertTrue(any('Prefill error' in msg for msg in cm.output))

    def test_form_initial_assignment_device_resolution(self):
        device = self.devices[0]
        ct = ContentType.objects.get_for_model(Device)

        form = self.model_form_class(
            initial={
                'assigned_object_type': ct.pk,
                'assigned_object_id': device.pk,
            }
        )

        self.assertEqual(form.initial.get('device'), device.pk)

    def test_form_initial_assignment_virtualmachine_resolution(self):
        vm = self.virtualmachines[0]
        ct = ContentType.objects.get_for_model(vm.__class__)

        form = self.model_form_class(
            initial={
                'assigned_object_type': ct.pk,
                'assigned_object_id': vm.pk,
            }
        )

        self.assertEqual(form.initial.get('virtualmachine'), vm.pk)

    def test_form_prefill_single_zabbixserverassignment_sets_initial(self):
        """
        When exactly one ZabbixServerAssignment exists for the provided
        (assigned_object_type, assigned_object_id), the form should prefill
        initial['zabbixserver'] with that assignment's id.
        """
        device = self.devices[0]
        ct = ContentType.objects.get_for_model(Device)

        assignment = ZabbixServerAssignment.objects.create(
            zabbixserver=self.zabbix_servers[0],
            assigned_object_type=ct,
            assigned_object_id=device.pk,
        )

        form = ZabbixHostInterfaceForm(
            initial={
                'assigned_object_type': ct.pk,
                'assigned_object_id': device.pk,
            }
        )

        # IMPORTANT: the code sets initial['zabbixserver'] = assignment.id (assignment PK),
        # not the ZabbixServer PK.
        self.assertEqual(form.initial.get('zabbixserver'), assignment.id)

    def test_form_prefill_no_zabbixserverassignment_does_not_set_initial(self):
        """
        When no ZabbixServerAssignment exists, the form should not set
        initial['zabbixserver'].
        """
        device = self.devices[1]
        ct = ContentType.objects.get_for_model(Device)

        # Ensure there is no assignment for this (ct, id)
        ZabbixServerAssignment.objects.filter(
            assigned_object_type=ct,
            assigned_object_id=device.pk,
        ).delete()

        form = ZabbixHostInterfaceForm(
            initial={
                'assigned_object_type': ct.pk,
                'assigned_object_id': device.pk,
            }
        )
        self.assertNotIn('zabbixserver', form.initial)

    def test_form_prefill_multiple_zabbixserverassignments_is_ignored(self):
        """
        When multiple ZabbixServerAssignment rows exist for the same
        (assigned_object_type, assigned_object_id), the form should ignore
        and leave initial['zabbixserver'] unset (MultipleObjectsReturned path).
        """
        device = self.devices[2]
        ct = ContentType.objects.get_for_model(Device)

        # Create two assignments for the same object (different servers).
        ZabbixServerAssignment.objects.create(
            zabbixserver=self.zabbix_servers[0],
            assigned_object_type=ct,
            assigned_object_id=device.pk,
        )
        ZabbixServerAssignment.objects.create(
            zabbixserver=self.zabbix_servers[1],
            assigned_object_type=ct,
            assigned_object_id=device.pk,
        )

        form = ZabbixHostInterfaceForm(
            initial={
                'assigned_object_type': ct.pk,
                'assigned_object_id': device.pk,
            }
        )

        # Multiple matches should be ignored by the form's __init__ logic
        self.assertNotIn('zabbixserver', form.initial)

    def _get_base_url(self):
        return 'plugins:nbxsync:zabbixhostinterface_{}'
