from django.urls import reverse

from utilities.testing import ViewTestCases

from nbxsync.choices import ZabbixProxyTypeChoices
from nbxsync.models import ZabbixProxy, ZabbixProxyGroup, ZabbixServer


class ZabbixProxyGroupTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ZabbixProxyGroup

    @classmethod
    def setUpTestData(cls):
        cls.zabbixserver = [
            ZabbixServer.objects.create(
                name='Zabbix Server A',
                description='Test Server',
                url='http://example.com',
                token='dummy-token',
                validate_certs=True,
            ),
            ZabbixServer.objects.create(
                name='Zabbix Server B',
                description='Test Server',
                url='http://example_b.com',
                token='dummy-token',
                validate_certs=True,
            ),
        ]

        zabbix_proxies = [
            ZabbixProxy(
                name='Proxy #1',
                zabbixserver=cls.zabbixserver[0],
                local_address='192.168.1.1',
                operating_mode=ZabbixProxyTypeChoices.ACTIVE,
            ),
        ]
        ZabbixProxy.objects.bulk_create(zabbix_proxies)

        zabbix_proxygroups = [
            ZabbixProxyGroup(
                name='Proxy Test Group A',
                zabbixserver=cls.zabbixserver[0],
                description='ProxyGroup',
                failover_delay='1m',
                min_online=1,
            ),
            ZabbixProxyGroup(
                name='Proxy Test Group B',
                zabbixserver=cls.zabbixserver[1],
                description='ProxyGroup',
                failover_delay='1m',
                min_online=1,
            ),
        ]

        ZabbixProxyGroup.objects.bulk_create(zabbix_proxygroups)

        cls.form_data = {
            'name': 'ProxyGroup Test X',
            'zabbixserver': cls.zabbixserver[0].id,
            'min_online': 1,
        }

        cls.bulk_edit_data = {
            'min_online': 5,
        }

    def test_proxygroup_detail_view_includes_assignment_table_being_none(self):
        # Make the user superuser so we dont have to worry about *any* permissions
        self.user.is_superuser = True
        self.user.save()

        proxygroup = ZabbixProxyGroup.objects.all().first()
        url = self._get_detail_url(proxygroup)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('objectassignment_table', response.context)

        table = response.context['objectassignment_table']
        self.assertIsNone(table)

    def test_proxygroup_detail_view_includes_assignment_table(self):
        # Make the user superuser so we dont have to worry about *any* permissions
        self.user.is_superuser = True
        self.user.save()

        proxygroup = ZabbixProxyGroup.objects.all().first()
        proxy = ZabbixProxy.objects.all().first()
        proxy.proxygroup = proxygroup
        proxy.save()

        url = self._get_detail_url(proxygroup)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('objectassignment_table', response.context)

        table = response.context['objectassignment_table']
        self.assertIsNotNone(table)
        self.assertGreater(len(table.rows), 0)

    def _get_base_url(self):
        return 'plugins:nbxsync:zabbixproxygroup_{}'

    def _get_detail_url(self, instance):
        return reverse('plugins:nbxsync:zabbixproxygroup', args=[instance.pk])
