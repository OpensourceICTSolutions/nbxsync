from django.urls import reverse

from utilities.testing import APIViewTestCases

from nbxsync.models import ZabbixServer, ZabbixTemplate, ZabbixTemplateRule


class ZabbixTemplateRuleAPITestCase(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.CreateObjectViewTestCase,
    APIViewTestCases.UpdateObjectViewTestCase,
    APIViewTestCases.DeleteObjectViewTestCase,
):
    model = ZabbixTemplateRule
    view_namespace = 'plugins-api:nbxsync'
    brief_fields = ['display', 'enabled', 'id', 'name', 'pattern', 'url']

    @classmethod
    def setUpTestData(cls):
        server = ZabbixServer.objects.create(name='Rule API Server', url='http://zabbix.local', token='abc123', validate_certs=True)
        template = ZabbixTemplate.objects.create(name='Windows by Zabbix agent', zabbixserver=server, templateid=10081)

        ZabbixTemplateRule.objects.bulk_create(
            [
                ZabbixTemplateRule(name='Windows', pattern='Windows', zabbixtemplate=template),
                ZabbixTemplateRule(name='Linux', pattern='Ubuntu|Debian', zabbixtemplate=template),
                ZabbixTemplateRule(name='Network', pattern='IOS|JunOS', zabbixtemplate=template),
            ]
        )

        cls.create_data = [
            {'name': 'API Rule 1', 'pattern': 'Windows Server 2019', 'zabbixtemplate': template.pk},
            {'name': 'API Rule 2', 'pattern': 'Windows Server 2022', 'zabbixtemplate': template.pk, 'priority': 10},
            {'name': 'API Rule 3', 'pattern': 'RHEL [89]', 'zabbixtemplate': template.pk, 'enabled': False},
        ]

        cls.bulk_update_data = {
            'enabled': False,
        }

    def test_invalid_pattern_is_rejected(self):
        self.add_permissions('nbxsync.add_zabbixtemplaterule')
        template = ZabbixTemplate.objects.first()

        response = self.client.post(
            reverse('plugins-api:nbxsync-api:zabbixtemplaterule-list'),
            {'name': 'Broken', 'pattern': 'Windows (', 'zabbixtemplate': template.pk},
            format='json',
            **self.header,
        )

        self.assertHttpStatus(response, 400)
        self.assertIn('pattern', response.data)
        self.assertFalse(ZabbixTemplateRule.objects.filter(name='Broken').exists())
