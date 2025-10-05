from utilities.testing import ViewTestCases

from nbxsync.choices import ZabbixProxyTypeChoices, ZabbixTLSChoices
from nbxsync.models import ZabbixProxy, ZabbixProxyGroup, ZabbixServer


class ZabbixProxyTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ZabbixProxy

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
        cls.proxygroup = [
            ZabbixProxyGroup.objects.create(name='Proxy Group A', zabbixserver=cls.zabbixserver[0]),
            ZabbixProxyGroup.objects.create(name='Proxy Group B', zabbixserver=cls.zabbixserver[1]),
        ]

        zabbix_proxies = [
            ZabbixProxy(
                name='Active Proxy #1',
                zabbixserver=cls.zabbixserver[0],
                proxygroup=cls.proxygroup[0],
                local_address='192.168.1.1',
                operating_mode=ZabbixProxyTypeChoices.ACTIVE,
            ),
            ZabbixProxy(
                name='Active Proxy #2',
                zabbixserver=cls.zabbixserver[1],
                proxygroup=cls.proxygroup[1],
                local_address='192.168.1.2',
                operating_mode=ZabbixProxyTypeChoices.ACTIVE,
            ),
        ]
        ZabbixProxy.objects.bulk_create(zabbix_proxies)

        cls.form_data = {
            'name': 'Proxy X',
            'zabbixserver': cls.zabbixserver[0].id,
            'proxygroup': cls.proxygroup[0].id,
            'operating_mode': ZabbixProxyTypeChoices.ACTIVE,
            'local_address': '192.0.2.100',  # Required if no proxygroup and ACTIVE
            'local_port': 10051,
            'description': 'A test proxy',
            'tls_connect': ZabbixTLSChoices.NO_ENCRYPTION,
            'tls_accept': [ZabbixTLSChoices.NO_ENCRYPTION],
        }

        cls.bulk_edit_data = {
            'zabbixserver': cls.zabbixserver[0].id,
        }

    def _get_base_url(self):
        return 'plugins:nbxsync:zabbixproxy_{}'
