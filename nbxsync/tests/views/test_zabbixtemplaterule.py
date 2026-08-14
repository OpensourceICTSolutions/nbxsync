from django.urls import reverse

from utilities.testing import ViewTestCases

from nbxsync.models import ZabbixServer, ZabbixTemplate, ZabbixTemplateRule


class ZabbixTemplateRuleTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ZabbixTemplateRule

    def _get_base_url(self):
        return 'plugins:nbxsync:zabbixtemplaterule_{}'

    @classmethod
    def setUpTestData(cls):
        server = ZabbixServer.objects.create(name='Rule View Server', url='http://zabbix.local', token='abc123', validate_certs=True)
        cls.templates = [
            ZabbixTemplate.objects.create(name='Windows by Zabbix agent', zabbixserver=server, templateid=10081),
            ZabbixTemplate.objects.create(name='Linux by Zabbix agent', zabbixserver=server, templateid=10001),
        ]

        ZabbixTemplateRule.objects.bulk_create(
            [
                ZabbixTemplateRule(name='Windows', pattern='Windows', zabbixtemplate=cls.templates[0]),
                ZabbixTemplateRule(name='Linux', pattern='Ubuntu|Debian', zabbixtemplate=cls.templates[1]),
                ZabbixTemplateRule(name='Disabled', pattern='Nothing', zabbixtemplate=cls.templates[1], enabled=False),
            ]
        )

        cls.form_data = {
            'name': 'FormRule',
            'description': 'Rule created through the form',
            'pattern': 'Windows Server 20[0-9]{2}',
            'zabbixtemplate': cls.templates[0].pk,
            'enabled': True,
            'priority': 50,
        }

        cls.bulk_edit_data = {
            'priority': 500,
            'enabled': False,
        }

    def test_invalid_pattern_is_rejected_by_the_form(self):
        self.add_permissions('nbxsync.add_zabbixtemplaterule')
        data = dict(self.form_data, name='BrokenRule', pattern='Windows (')

        response = self.client.post(reverse('plugins:nbxsync:zabbixtemplaterule_add'), data)

        self.assertHttpStatus(response, 200)
        self.assertFalse(ZabbixTemplateRule.objects.filter(name='BrokenRule').exists())
