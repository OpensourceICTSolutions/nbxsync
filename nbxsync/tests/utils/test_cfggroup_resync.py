from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from types import SimpleNamespace
from dcim.models import Device
from ipam.models import IPAddress
from utilities.testing import create_test_device

from nbxsync.jobs.cfggroup import PropagateConfigGroupAssignmentJob, DeleteConfigGroupAssignmentChildrenJob
from nbxsync.models import ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment, ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixHostInterface, ZabbixMacro, ZabbixMacroAssignment, ZabbixServer, ZabbixServerAssignment, ZabbixTag, ZabbixTagAssignment, ZabbixTemplate, ZabbixTemplateAssignment
from nbxsync.signals.zabbixconfigurationgroupassignment import handle_postsave_zabbixconfigurationgroupassignment, handle_postdelete_zabbixconfigurationgroupassignment
from nbxsync.utils.cfggroup.helpers import get_configgroup_ct_id
from nbxsync.utils.cfggroup.resync_zabbixconfiggroupassignment import resync_zabbixconfigurationgroupassignment

# Patches needed whenever a job that calls propagate_group_assignment or
# delete_group_clones runs synchronously in tests.
_PATCH_HELPERS_ON_COMMIT = patch(
    'nbxsync.utils.cfggroup.helpers.transaction.on_commit',
    side_effect=lambda fn: fn(),
)
_PATCH_RESYNC_ON_COMMIT = patch(
    'nbxsync.utils.cfggroup.resync_zabbixconfiggroupassignment.transaction.on_commit',
    side_effect=lambda fn: fn(),
)
_PATCH_JOBS_ON_COMMIT = patch(
    'nbxsync.jobs.cfggroup.transaction.on_commit',
    side_effect=lambda fn: fn(),
)


class ZabbixConfigurationGroupAssignmentSignalsTestCase(TestCase):
    def setUp(self):
        if hasattr(get_configgroup_ct_id, '_ct_id'):
            delattr(get_configgroup_ct_id, '_ct_id')

        self.server = ZabbixServer.objects.create(name='CfgGroup Signal Server')
        self.template = ZabbixTemplate.objects.create(name='CfgGroup Template', templateid=1001, zabbixserver=self.server)
        self.tag = ZabbixTag.objects.create(name='Env', tag='env', value='prod')
        self.hostgroup = ZabbixHostgroup.objects.create(name='CfgGroup Hostgroup', value='hg-cfg', zabbixserver=self.server)
        self.macro = ZabbixMacro.objects.create(macro='{$CFG_MACRO}', value='macro-val', description='Configgroup macro', type='hg')
        self.cfg = ZabbixConfigurationGroup.objects.create(name='ConfigGroup Signals', description='Assignment signal test group')

        self.devices = [
            create_test_device(name='CfgGroup Dev 1'),
            create_test_device(name='CfgGroup Dev 2'),
        ]

        for i, dev in enumerate(self.devices, start=1):
            ip = IPAddress.objects.create(address=f'10.0.{i}.1/32')
            dev.primary_ip4 = ip
            dev.save()

        self.device_ct = ContentType.objects.get_for_model(Device)
        self.cfg_ct = ContentType.objects.get_for_model(ZabbixConfigurationGroup)

    def _create_all_parent_assignments(self):
        self.server_parent = ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)
        self.template_parent = ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)
        self.tag_parent = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)
        self.hostgroup_parent = ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)
        self.macro_parent = ZabbixMacroAssignment.objects.create(zabbixmacro=self.macro, is_regex=False, context='', value='macro-val', assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)
        self.hostinterface_parent = ZabbixHostInterface.objects.create(zabbixserver=self.server, type=1, useip=1, interface_type=1, ip=IPAddress.objects.create(address='192.0.2.1/32'), port=10051, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

    @patch('nbxsync.signals.zabbixconfigurationgroupassignment.propagate_configgroup_assignment')
    def test_postsave_enqueues_job_with_correct_pk(self, mock_job):
        asn = ZabbixConfigurationGroupAssignment(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)
        asn.pk = 999

        handle_postsave_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=asn, created=True)

        mock_job.delay.assert_called_once_with(asn.pk)

    @patch('nbxsync.signals.zabbixconfigurationgroupassignment.propagate_configgroup_assignment')
    def test_postsave_returns_early_when_configgroup_none(self, mock_job):
        asn = SimpleNamespace(zabbixconfigurationgroup=None)

        handle_postsave_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=asn, created=True)

        mock_job.delay.assert_not_called()

    @patch('nbxsync.signals.zabbixconfigurationgroupassignment.delete_configgroup_assignment_children')
    def test_postdelete_enqueues_job_with_correct_args(self, mock_job):
        asn = ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        handle_postdelete_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=asn)

        mock_job.delay.assert_called_once_with(configgroup_pk=self.cfg.pk, assigned_object_type_pk=self.device_ct.pk, assigned_object_id=self.devices[0].pk)

    @patch('nbxsync.signals.zabbixconfigurationgroupassignment.delete_configgroup_assignment_children')
    def test_postdelete_returns_early_when_configgroup_none(self, mock_job):
        asn = SimpleNamespace(zabbixconfigurationgroup=None, assigned_object_type_id=None, assigned_object_id=None)

        handle_postdelete_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=asn)

        mock_job.delay.assert_not_called()

    @_PATCH_HELPERS_ON_COMMIT
    @_PATCH_RESYNC_ON_COMMIT
    def test_postsave_job_creates_children_for_member(self, *_mocks):
        self._create_all_parent_assignments()

        asn = ZabbixConfigurationGroupAssignment.objects.create(
            zabbixconfigurationgroup=self.cfg,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.devices[0].pk,
        )

        PropagateConfigGroupAssignmentJob(assignment_pk=asn.pk).run()

        server_clone = ZabbixServerAssignment.objects.filter(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk).first()
        self.assertIsNotNone(server_clone)
        self.assertEqual(server_clone.zabbixconfigurationgroup, self.cfg)

        template_clone = ZabbixTemplateAssignment.objects.filter(zabbixtemplate=self.template, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk).first()
        self.assertIsNotNone(template_clone)
        self.assertEqual(template_clone.zabbixconfigurationgroup, self.cfg)

        tag_clone = ZabbixTagAssignment.objects.filter(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk).first()
        self.assertIsNotNone(tag_clone)
        self.assertEqual(tag_clone.zabbixconfigurationgroup, self.cfg)

        hg_clone = ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk).first()
        self.assertIsNotNone(hg_clone)
        self.assertEqual(hg_clone.zabbixconfigurationgroup, self.cfg)

        macro_clone = ZabbixMacroAssignment.objects.filter(zabbixmacro=self.macro, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk).first()
        self.assertIsNotNone(macro_clone)
        self.assertEqual(macro_clone.zabbixconfigurationgroup, self.cfg)
        self.assertEqual(macro_clone.parent, self.macro_parent)

        hi_clone = ZabbixHostInterface.objects.filter(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk, parent=self.hostinterface_parent).first()
        self.assertIsNotNone(hi_clone, 'Expected a host interface clone for device')
        self.assertEqual(hi_clone.zabbixconfigurationgroup, self.cfg)
        self.assertEqual(hi_clone.ip, self.devices[0].primary_ip)
        self.assertEqual(hi_clone.interface_type, self.hostinterface_parent.interface_type)
        self.assertEqual(hi_clone.type, self.hostinterface_parent.type)
        self.assertEqual(hi_clone.port, self.hostinterface_parent.port)

    def test_postsave_job_returns_early_when_assignment_not_found(self):
        """Job with a non-existent pk should be a no-op."""
        before = {
            'server': ZabbixServerAssignment.objects.count(),
            'template': ZabbixTemplateAssignment.objects.count(),
        }

        PropagateConfigGroupAssignmentJob(assignment_pk=999999).run()

        self.assertEqual(ZabbixServerAssignment.objects.count(), before['server'])
        self.assertEqual(ZabbixTemplateAssignment.objects.count(), before['template'])

    @_PATCH_HELPERS_ON_COMMIT
    @_PATCH_RESYNC_ON_COMMIT
    def test_postdelete_job_deletes_children_for_one_assignment_only(self, *_mocks):
        self._create_all_parent_assignments()

        asn1 = ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)
        asn2 = ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[1].pk)

        PropagateConfigGroupAssignmentJob(assignment_pk=asn1.pk).run()
        PropagateConfigGroupAssignmentJob(assignment_pk=asn2.pk).run()

        def has_clones_for(dev):
            return all(
                qs.filter(assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg).exists()
                for qs in [
                    ZabbixServerAssignment.objects.filter(zabbixserver=self.server),
                    ZabbixTemplateAssignment.objects.filter(zabbixtemplate=self.template),
                    ZabbixTagAssignment.objects.filter(zabbixtag=self.tag),
                    ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup),
                    ZabbixMacroAssignment.objects.filter(zabbixmacro=self.macro),
                    ZabbixHostInterface.objects.filter(zabbixserver=self.server),
                ]
            )

        self.assertTrue(has_clones_for(self.devices[0]))
        self.assertTrue(has_clones_for(self.devices[1]))

        DeleteConfigGroupAssignmentChildrenJob(configgroup_pk=self.cfg.pk, assigned_object_type_pk=self.device_ct.pk, assigned_object_id=self.devices[0].pk).run()

        def has_any_clones_for(dev):
            return any(
                qs.filter(assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg).exists()
                for qs in [
                    ZabbixServerAssignment.objects.filter(zabbixserver=self.server),
                    ZabbixTemplateAssignment.objects.filter(zabbixtemplate=self.template),
                    ZabbixTagAssignment.objects.filter(zabbixtag=self.tag),
                    ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup),
                    ZabbixMacroAssignment.objects.filter(zabbixmacro=self.macro),
                    ZabbixHostInterface.objects.filter(zabbixserver=self.server),
                ]
            )

        self.assertFalse(has_any_clones_for(self.devices[0]))
        self.assertTrue(has_clones_for(self.devices[1]))

    @_PATCH_HELPERS_ON_COMMIT
    @_PATCH_RESYNC_ON_COMMIT
    def test_resync_creates_children_for_all_members(self, *_mocks):
        self._create_all_parent_assignments()

        asn1 = ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)
        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[1].pk)

        resync_zabbixconfigurationgroupassignment(asn1)

        def has_clones_for(dev):
            return all(
                qs.filter(assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg).exists()
                for qs in [
                    ZabbixServerAssignment.objects.filter(zabbixserver=self.server),
                    ZabbixTemplateAssignment.objects.filter(zabbixtemplate=self.template),
                    ZabbixTagAssignment.objects.filter(zabbixtag=self.tag),
                    ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup),
                    ZabbixMacroAssignment.objects.filter(zabbixmacro=self.macro),
                    ZabbixHostInterface.objects.filter(zabbixserver=self.server),
                ]
            )

        self.assertTrue(has_clones_for(self.devices[0]))
        self.assertTrue(has_clones_for(self.devices[1]))

        for dev in self.devices:
            macro_clone = ZabbixMacroAssignment.objects.get(zabbixmacro=self.macro, assigned_object_type=self.device_ct, assigned_object_id=dev.pk, zabbixconfigurationgroup=self.cfg)
            self.assertEqual(macro_clone.parent, self.macro_parent)

    def test_resync_returns_early_when_configgroup_none(self):
        from types import SimpleNamespace

        instance = SimpleNamespace(zabbixconfigurationgroup=None)

        resync_zabbixconfigurationgroupassignment(instance)

        self.assertEqual(ZabbixServerAssignment.objects.count(), 0)
        self.assertEqual(ZabbixTemplateAssignment.objects.count(), 0)
        self.assertEqual(ZabbixTagAssignment.objects.count(), 0)
        self.assertEqual(ZabbixHostgroupAssignment.objects.count(), 0)
        self.assertEqual(ZabbixMacroAssignment.objects.count(), 0)
        self.assertEqual(ZabbixHostInterface.objects.count(), 0)

    @_PATCH_HELPERS_ON_COMMIT
    @_PATCH_RESYNC_ON_COMMIT
    def test_resync_hostinterface_skips_members_without_primary_ip(self, *_mocks):
        hostinterface_parent = ZabbixHostInterface.objects.create(zabbixserver=self.server, type=1, useip=1, interface_type=1, ip=IPAddress.objects.create(address='192.0.2.20/32'), port=10051, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        dev_with_ip = self.devices[0]
        dev_no_ip = create_test_device(name='CfgGroup Dev No IP (resync)')

        asn_with_ip = ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=dev_with_ip.pk)
        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=dev_no_ip.pk)

        resync_zabbixconfigurationgroupassignment(asn_with_ip)

        self.assertTrue(ZabbixHostInterface.objects.filter(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=dev_with_ip.pk, parent=hostinterface_parent).exists())
        self.assertFalse(ZabbixHostInterface.objects.filter(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=dev_no_ip.pk, parent=hostinterface_parent).exists())

    @_PATCH_HELPERS_ON_COMMIT
    @_PATCH_RESYNC_ON_COMMIT
    def test_hostinterface_sync_skips_members_without_primary_ip(self, *_mocks):
        hostinterface_parent = ZabbixHostInterface.objects.create(zabbixserver=self.server, type=1, useip=1, interface_type=1, ip=IPAddress.objects.create(address='192.0.2.10/32'), port=10051, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        dev_with_ip = self.devices[0]
        dev_no_ip = create_test_device(name='CfgGroup Dev No IP')

        assignment_with_ip = ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=dev_with_ip.pk)
        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=dev_no_ip.pk)

        PropagateConfigGroupAssignmentJob(assignment_pk=assignment_with_ip.pk).run()

        self.assertTrue(ZabbixHostInterface.objects.filter(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=dev_with_ip.pk, parent=hostinterface_parent).exists())
        self.assertFalse(ZabbixHostInterface.objects.filter(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=dev_no_ip.pk, parent=hostinterface_parent).exists())
