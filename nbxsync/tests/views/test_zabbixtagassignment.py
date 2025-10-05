from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from dcim.models import Device
from utilities.testing import ViewTestCases, create_test_device, create_test_virtualmachine

from nbxsync.forms import ZabbixTagAssignmentForm
from nbxsync.models import ZabbixTag, ZabbixTagAssignment


class ZabbixTagAssignmentTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = ZabbixTagAssignment

    @classmethod
    def setUpTestData(cls):
        cls.devices = [
            create_test_device(name='Tag Assignment Test Device 1'),
            create_test_device(name='Tag Assignment Test Device 2'),
            create_test_device(name='Tag Assignment Test Device 3'),
            create_test_device(name='Tag Assignment Test Device 4'),
        ]
        cls.virtualmachines = [create_test_virtualmachine(name='Tag Assignment Test VM 1')]
        cls.device_ct = ContentType.objects.get_for_model(Device)
        cls.zabbix_tags = [
            ZabbixTag(name='Tag 1', description='Bla', tag='tag 1', value='bla'),
            ZabbixTag(name='Tag 2', description='Bla', tag='tag 2', value='bla'),
            ZabbixTag(name='Tag 3', description='Bla', tag='tag 3', value='bla'),
            ZabbixTag(name='Tag 4', description='Bla', tag='tag 4', value='bla'),
        ]
        ZabbixTag.objects.bulk_create(cls.zabbix_tags)

        zabbix_tagassignments = [
            ZabbixTagAssignment(zabbixtag=cls.zabbix_tags[0], assigned_object_type=cls.device_ct, assigned_object_id=cls.devices[0].id),
            ZabbixTagAssignment(zabbixtag=cls.zabbix_tags[1], assigned_object_type=cls.device_ct, assigned_object_id=cls.devices[1].id),
        ]
        ZabbixTagAssignment.objects.bulk_create(zabbix_tagassignments)

        cls.form_data = {'zabbixtag': cls.zabbix_tags[2].id, 'device': cls.devices[2].id}

    def test_tagassignment_form_prefills_assigned_object(self):
        self.user.is_superuser = True
        self.user.save()

        url = reverse('plugins:nbxsync:zabbixtagassignment_add')
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

    def test_tagassignment_form_invalid_content_type_triggers_prefill_exception(self):
        self.user.is_superuser = True
        self.user.save()

        # Use a clearly invalid content type ID
        invalid_ct_id = 99999  # unlikely to exist
        invalid_obj_id = 12345

        with self.assertLogs('nbxsync.forms', level='DEBUG') as cm:
            url = reverse('plugins:nbxsync:zabbixtagassignment_add')
            response = self.client.get(
                url,
                {'assigned_object_type': invalid_ct_id, 'assigned_object_id': invalid_obj_id},
            )
            self.assertEqual(response.status_code, 200)

        # Verify our except path executed and logged
        self.assertTrue(any('Prefill error' in msg for msg in cm.output))

    def test_clean_raises_if_multiple_assignments(self):
        form = ZabbixTagAssignmentForm(
            data={
                'device': self.devices[0].pk,
                'virtualmachine': self.virtualmachines[0].pk,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('virtualmachine', form.errors)
        self.assertIn('A Tag can only be assigned to a single object.', form.errors['virtualmachine'][0])

    def test_clean_sets_assigned_object_none_if_unassigned(self):
        form = ZabbixTagAssignmentForm(data={'zabbixtag': str(self.zabbix_tags[0].id)})

        form.is_valid()

        # Should not raise and assigned_object should be None
        self.assertIsNone(form.instance.assigned_object)

    def _get_base_url(self):
        return 'plugins:nbxsync:zabbixtagassignment_{}'
