from django.urls import reverse

from utilities.testing import ViewTestCases

from nbxsync.choices import HostInterfaceRequirementChoices
from nbxsync.models import ZabbixServer, ZabbixTemplate


class ZabbixServerTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ZabbixServer

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

        cls.templates = [
            ZabbixTemplate(
                name='Template X',
                templateid=1001,
                zabbixserver=cls.zabbix_servers[0],
                interface_requirements=[HostInterfaceRequirementChoices.AGENT, HostInterfaceRequirementChoices.ANY],
            ),
            ZabbixTemplate(
                name='Template Y',
                templateid=1002,
                zabbixserver=cls.zabbix_servers[0],
                interface_requirements=[HostInterfaceRequirementChoices.AGENT, HostInterfaceRequirementChoices.ANY],
            ),
        ]
        ZabbixTemplate.objects.bulk_create(cls.templates)

        ZabbixTemplate.objects.create(
            name='Unrelated Template',
            templateid=2000,
            zabbixserver=cls.zabbix_servers[1],
            interface_requirements=[HostInterfaceRequirementChoices.AGENT, HostInterfaceRequirementChoices.ANY],
        )

        cls.form_data = {
            'name': 'Zabbix Server Form',
            'description': 'Test Server 1',
            'url': 'http://zabbixform.com',
            'token': 'from-token',
            'validate_certs': True,
        }

        cls.bulk_edit_data = {
            'description': 'Test Server 31',
            'token': 'edit-token',
            'validate_certs': False,
        }

    def test_zabbixserver_templates_view(self):
        # Make the user superuser so we dont have to worry about *any* permissions
        self.user.is_superuser = True
        self.user.save()

        url = reverse('plugins:nbxsync:zabbixserver_templates', args=[self.zabbix_servers[0].pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Template X', content)
        self.assertIn('Template Y', content)
        self.assertNotIn('Unrelated Template', content)

    def _get_base_url(self):
        return 'plugins:nbxsync:zabbixserver_{}'
