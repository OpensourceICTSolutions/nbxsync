from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from dcim.models import Device
from utilities.testing import ViewTestCases, create_test_device, create_test_virtualmachine

from nbxsync.forms import ZabbixConfigurationGroupAssignmentForm
from nbxsync.models import ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment


class ZabbixConfigurationGroupAssignmentViewTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ZabbixConfigurationGroupAssignment

    @classmethod
    def setUpTestData(cls):
        # Create two configuration groups

        cls.zabbix_configurationgroups = [
            ZabbixConfigurationGroup(
                name='Group1',
                description='Group 1',
            ),
            ZabbixConfigurationGroup(
                name='Group2',
                description='Group 2',
            ),
        ]
        ZabbixConfigurationGroup.objects.bulk_create(cls.zabbix_configurationgroups)

        # Create two devices
        cls.devices = [
            create_test_device(name='Test Device 1'),
            create_test_device(name='Test Device 2'),
            create_test_device(name='Test Device 3'),
            create_test_device(name='Test Device 4'),
        ]
        cls.virtualmachines = [create_test_virtualmachine(name='Configuration Group Test VM 1')]

        cls.device_ct = ContentType.objects.get_for_model(Device)

        # Seed a couple of assignments
        zabbix_configurationgroupassignments = [
            ZabbixConfigurationGroupAssignment(
                zabbixconfigurationgroup=cls.zabbix_configurationgroups[0],
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[0].id,
            ),
            ZabbixConfigurationGroupAssignment(
                zabbixconfigurationgroup=cls.zabbix_configurationgroups[0],
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[1].id,
            ),
            ZabbixConfigurationGroupAssignment(
                zabbixconfigurationgroup=cls.zabbix_configurationgroups[0],
                assigned_object_type=cls.device_ct,
                assigned_object_id=cls.devices[2].id,
            ),
        ]
        ZabbixConfigurationGroupAssignment.objects.bulk_create(zabbix_configurationgroupassignments)

        # Data for CreateObjectViewTestCase
        cls.form_data = {'zabbixconfigurationgroup': cls.zabbix_configurationgroups[0].id, 'device': cls.devices[3].id}

        cls.bulk_edit_data = {
            'zabbixconfigurationgroup': cls.zabbix_configurationgroups[1].id,
        }

    def _get_base_url(self):
        return 'plugins:nbxsync:zabbixconfigurationgroupassignment_{}'

    def test_hostgroupassignment_form_prefills_assigned_object(self):
        self.user.is_superuser = True
        self.user.save()

        url = reverse('plugins:nbxsync:zabbixconfigurationgroupassignment_add')
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
            url = reverse('plugins:nbxsync:zabbixconfigurationgroupassignment_add')
            response = self.client.get(
                url,
                {'assigned_object_type': invalid_ct_id, 'assigned_object_id': invalid_obj_id},
            )
            self.assertEqual(response.status_code, 200)

        # Verify our except path executed and logged
        self.assertTrue(any('Prefill error' in msg for msg in cm.output))

    def test_clean_raises_if_multiple_assignments(self):
        form = ZabbixConfigurationGroupAssignmentForm(
            data={
                'device': self.devices[0].pk,
                'virtualmachine': self.virtualmachines[0].pk,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('virtualmachine', form.errors)
        self.assertIn('A Zabbix Configuration Group can only be assigned to a single object.', form.errors['virtualmachine'][0])

    def test_clean_sets_assigned_object_none_if_unassigned(self):
        form = ZabbixConfigurationGroupAssignmentForm(data={'zabbixconfigurationgroup': str(self.zabbix_configurationgroups[0].id)})

        form.is_valid()

        # Should not raise and assigned_object should be None
        self.assertIsNone(form.instance.assigned_object)
