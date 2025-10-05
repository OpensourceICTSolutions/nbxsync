from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from virtualization.models import VirtualMachine

from dcim.models import Device
from utilities.testing import ViewTestCases, create_test_device, create_test_virtualmachine

from nbxsync.forms import ZabbixHostInventoryForm
from nbxsync.models import ZabbixHostInventory


class ZabbixHostInventoryTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ZabbixHostInventory

    @classmethod
    def setUpTestData(cls):
        cls.devices = [
            create_test_device(name='HostInventory Test Device 1'),
            create_test_device(name='HostInventory Test Device 2'),
            create_test_device(name='HostInventory Test Device 3'),
            create_test_device(name='HostInventory Test Device 4'),
        ]
        cls.virtualmachines = [create_test_virtualmachine(name='VM1')]

        cls.device_ct = ContentType.objects.get_for_model(Device)
        cls.virtualmachine_ct = ContentType.objects.get_for_model(VirtualMachine)

        zabbix_hostinventory = [
            ZabbixHostInventory(alias='Demo', assigned_object_type=cls.device_ct, assigned_object_id=cls.devices[0].id),
            ZabbixHostInventory(alias='Demo', assigned_object_type=cls.virtualmachine_ct, assigned_object_id=cls.virtualmachines[0].id),
        ]
        ZabbixHostInventory.objects.bulk_create(zabbix_hostinventory)

        cls.form_data = {
            'inventory_mode': 0,
            'device': cls.devices[1].id,
            'alias': 'Alias',
            'asset_tag': 'Asset Tag',
            'chassis': 'Chassis',
            'contact': 'Contact',
            'contract_number': 'Contract',
            'date_hw_decomm': 'Date HW Decom',
            'date_hw_expiry': 'Date HW Expiry',
            'date_hw_install': 'Date HW Install',
            'date_hw_purchase': 'Date HW Purchase',
            'deployment_status': 'Deployment status',
            'hardware': 'Hardware',
            'hardware_full': 'Hardware full',
            'host_netmask': 'Host netmask',
            'host_networks': 'Host networks',
            'host_router': 'Host router',
            'hw_arch': 'HW Arch',
            'installer_name': 'Installer',
            'location': 'Location',
            'location_lat': 'LAT',
            'location_lon': 'LON',
            'macaddress_a': 'MAC A',
            'macaddress_b': 'MAC B',
            'model_field': 'Model',
            'name': 'Name',
            'notes': 'Notes',
            'oob_ip': 'OOB IP',
            'oob_netmask': 'OOB Netmask',
            'oob_router': 'OOB Router',
            'os': 'OS',
            'os_full': 'OS Full',
            'os_short': 'OS Short',
            'poc_1_cell': 'POC 1 Cell',
            'poc_1_email': 'POC 1 Mail',
            'poc_1_name': 'POC 1 Name',
            'poc_1_notes': 'POC 1 Notes',
            'poc_1_phone_a': 'POC 1 Phone A',
            'poc_1_phone_b': 'POC 1 Phone B',
            'poc_1_screen ': 'POC 1 Screen',
            'poc_2_cell': 'POC 2 Cell',
            'poc_2_email': 'POC 2 Mail',
            'poc_2_name': 'POC 2 Name',
            'poc_2_notes': 'POC 2 Notes',
            'poc_2_phone_a': 'POC 2 Phone A',
            'poc_2_phone_b': 'POC 2 Phone B',
            'poc_2_screen': 'POC 2 Screen',
            'serialno_a': 'SN A',
            'serialno_b': 'SN B',
            'site_address_a': 'Site A',
            'site_address_b': 'Site B',
            'site_address_c': 'Site C',
            'site_city': 'Site City',
            'site_country': 'Site Country',
            'site_notes': 'Site Notes',
            'site_rack': 'Site Rack',
            'site_state': 'Site State',
            'site_zip': 'Site Zip',
            'software': 'Software',
            'software_app_a': 'SW APP A',
            'software_app_b': 'SW APP B',
            'software_app_c': 'SW APP C',
            'software_app_d': 'SW APP D',
            'software_app_e': 'SW APP E',
            'software_full': 'SW Full',
            'tag': 'TAG',
            'type': 'Type',
            'type_full': 'Type full',
            'url_a': 'URL A',
            'url_b': 'URL B',
            'url_c': 'URL C',
            'vendor': 'Vendor',
        }

        cls.bulk_edit_data = {
            'alias': 'Alias - UPDATE',
            'asset_tag': 'Asset Tag - UPDATE',
            'chassis': 'Chassis - UPDATE',
            'contact': 'Contact - UPDATE',
            'contract_number': 'Contract - UPDATE',
            'date_hw_decomm': 'Date HW Decom - UPDATE',
            'date_hw_expiry': 'Date HW Expiry - UPDATE',
            'date_hw_install': 'Date HW Install - UPDATE',
            'date_hw_purchase': 'Date HW Purchase - UPDATE',
            'deployment_status': 'Deployment status - UPDATE',
            'hardware': 'Hardware - UPDATE',
            'hardware_full': 'Hardware full - UPDATE',
            'host_netmask': 'Host netmask - UPDATE',
            'host_networks': 'Host networks - UPDATE',
            'host_router': 'Host router - UPDATE',
            'hw_arch': 'HW Arch - UPDATE',
            'installer_name': 'Installer - UPDATE',
            'location': 'Location - UPDATE',
            'location_lat': 'LAT - UPDATE',
            'location_lon': 'LON - UPDATE',
            'macaddress_a': 'MAC A - UPDATE',
            'macaddress_b': 'MAC B - UPDATE',
            'model_field': 'Model - UPDATE',
            'name': 'Name - UPDATE',
            'notes': 'Notes - UPDATE',
            'oob_ip': 'OOB IP - UPDATE',
            'oob_netmask': 'OOB Netmask - UPDATE',
            'oob_router': 'OOB Router - UPDATE',
            'os': 'OS - UPDATE',
            'os_full': 'OS Full - UPDATE',
            'os_short': 'OS Short - UPDATE',
            'poc_1_cell': 'POC 1 Cell - UPDATE',
            'poc_1_email': 'POC 1 Mail - UPDATE',
            'poc_1_name': 'POC 1 Name - UPDATE',
            'poc_1_notes': 'POC 1 Notes - UPDATE',
            'poc_1_phone_a': 'POC 1 Phone A - UPDATE',
            'poc_1_phone_b': 'POC 1 Phone B - UPDATE',
            'poc_1_screen ': 'POC 1 Screen - UPDATE',
            'poc_2_cell': 'POC 2 Cell - UPDATE',
            'poc_2_email': 'POC 2 Mail - UPDATE',
            'poc_2_name': 'POC 2 Name - UPDATE',
            'poc_2_notes': 'POC 2 Notes - UPDATE',
            'poc_2_phone_a': 'POC 2 Phone A - UPDATE',
            'poc_2_phone_b': 'POC 2 Phone B - UPDATE',
            'poc_2_screen': 'POC 2 Screen - UPDATE',
            'serialno_a': 'SN A - UPDATE',
            'serialno_b': 'SN B - UPDATE',
            'site_address_a': 'Site A - UPDATE',
            'site_address_b': 'Site B - UPDATE',
            'site_address_c': 'Site C - UPDATE',
            'site_city': 'Site City - UPDATE',
            'site_country': 'Site Country - UPDATE',
            'site_notes': 'Site Notes - UPDATE',
            'site_rack': 'Site Rack - UPDATE',
            'site_state': 'Site State - UPDATE',
            'site_zip': 'Site Zip - UPDATE',
            'software': 'Software - UPDATE',
            'software_app_a': 'SW APP A - UPDATE',
            'software_app_b': 'SW APP B - UPDATE',
            'software_app_c': 'SW APP C - UPDATE',
            'software_app_d': 'SW APP D - UPDATE',
            'software_app_e': 'SW APP E - UPDATE',
            'software_full': 'SW Full - UPDATE',
            'tag': 'TAG - UPDATE',
            'type': 'Type - UPDATE',
            'type_full': 'Type full - UPDATE',
            'url_a': 'URL A - UPDATE',
            'url_b': 'URL B - UPDATE',
            'url_c': 'URL C - UPDATE',
            'vendor': 'Vendor - UPDATE',
        }

    def test_inventory_form_prefills_assigned_object(self):
        self.user.is_superuser = True
        self.user.save()

        url = reverse('plugins:nbxsync:zabbixhostinventory_add')
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

    def test_inventory_form_invalid_content_type_triggers_prefill_exception(self):
        self.user.is_superuser = True
        self.user.save()

        # Use a clearly invalid content type ID
        invalid_ct_id = 99999  # unlikely to exist
        invalid_obj_id = 12345

        with self.assertLogs('nbxsync.forms', level='DEBUG') as cm:
            url = reverse('plugins:nbxsync:zabbixhostinventory_add')
            response = self.client.get(
                url,
                {'assigned_object_type': invalid_ct_id, 'assigned_object_id': invalid_obj_id},
            )
            self.assertEqual(response.status_code, 200)

        # Verify our except path executed and logged
        self.assertTrue(any('Prefill error' in msg for msg in cm.output))

    def test_clean_raises_if_multiple_assignments(self):
        form = ZabbixHostInventoryForm(
            data={
                'device': self.devices[0].pk,
                'virtualmachine': self.virtualmachines[0].pk,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('virtualmachine', form.errors)
        self.assertIn('only be assigned to one object', form.errors['virtualmachine'][0])

    def test_clean_sets_assigned_object_none_if_unassigned(self):
        form = ZabbixHostInventoryForm(data={'alias': 'Unassigned Inventory'})

        form.is_valid()

        # Should not raise and assigned_object should be None
        self.assertIsNone(form.instance.assigned_object)

    def _get_base_url(self):
        return 'plugins:nbxsync:zabbixhostinventory_{}'
