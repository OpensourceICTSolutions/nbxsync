from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from dcim.models import Device
from utilities.testing import ViewTestCases, create_test_device

from nbxsync.models import ZabbixTag, ZabbixTagAssignment


class ZabbixTagTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ZabbixTag

    @classmethod
    def setUpTestData(cls):
        cls.devices = [
            create_test_device(name='Tag Assignment Test Device 1'),
            create_test_device(name='Tag Assignment Test Device 2'),
            create_test_device(name='Tag Assignment Test Device 3'),
            create_test_device(name='Tag Assignment Test Device 4'),
        ]
        device_ct = ContentType.objects.get_for_model(Device)
        cls.zabbix_tags = [
            ZabbixTag(name='Tag 1', description='Bla', tag='tag 1', value='bla'),
            ZabbixTag(name='Tag 2', description='Bla', tag='tag 2', value='bla'),
        ]
        ZabbixTag.objects.bulk_create(cls.zabbix_tags)

        zabbix_tagassignments = [
            ZabbixTagAssignment(zabbixtag=cls.zabbix_tags[0], assigned_object_type=device_ct, assigned_object_id=cls.devices[0].id),
        ]
        ZabbixTagAssignment.objects.bulk_create(zabbix_tagassignments)

        cls.form_data = {
            'name': 'FormTag',
            'description': 'FormTag Description',
            'tag': 'TagForm',
            'value': 'BlaBla',
        }

        cls.bulk_edit_data = {
            'description': 'New description',
        }

    def test_tag_detail_view_includes_assignment_table_being_none(self):
        # Make the user superuser so we dont have to worry about *any* permissions
        self.user.is_superuser = True
        self.user.save()

        url = self._get_detail_url(self.zabbix_tags[1])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('objectassignment_table', response.context)

        table = response.context['objectassignment_table']
        self.assertIsNone(table)

    def test_tag_detail_view_includes_assignment_table(self):
        # Make the user superuser so we dont have to worry about *any* permissions
        self.user.is_superuser = True
        self.user.save()

        url = self._get_detail_url(self.zabbix_tags[0])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('objectassignment_table', response.context)

        table = response.context['objectassignment_table']
        self.assertIsNotNone(table)
        self.assertGreater(len(table.rows), 0)

    def _get_base_url(self):
        return 'plugins:nbxsync:zabbixtag_{}'

    def _get_detail_url(self, instance):
        return reverse('plugins:nbxsync:zabbixtag', args=[instance.pk])
