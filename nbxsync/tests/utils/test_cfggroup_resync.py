from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import TransactionTestCase

from utilities.testing import create_test_device
from dcim.models import Device
from ipam.models import IPAddress

from nbxsync.models import ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment, ZabbixServer, ZabbixServerAssignment, ZabbixTemplate, ZabbixTemplateAssignment, ZabbixTag, ZabbixTagAssignment, ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixMacro, ZabbixMacroAssignment, ZabbixHostInterface
from nbxsync.utils.cfggroup.helpers import get_configgroup_ct_id
from nbxsync.signals.zabbixconfigurationgroupassignment import handle_postsave_zabbixconfigurationgroupassignment, handle_postdelete_zabbixconfigurationgroupassignment
from nbxsync.utils.cfggroup.resync_zabbixconfiggroupassignment import resync_zabbixconfigurationgroupassignment


class ZabbixConfigurationGroupAssignmentSignalsTestCase(TransactionTestCase):
    def setUp(self):
        # Reset cached content type on helper if present
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

        # Give each device a primary IP
        for i, dev in enumerate(self.devices, start=1):
            ip = IPAddress.objects.create(address=f'10.0.{i}.1/32')
            # NetBox uses primary_ip4 backing primary_ip
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

    @patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda fn: fn())
    @patch('nbxsync.signals.zabbixconfigurationgroupassignment.transaction.on_commit', side_effect=lambda fn: fn())
    def test_postsave_creates_children_for_member(self, *_mocks):
        self._create_all_parent_assignments()

        asn = ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        handle_postsave_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=asn, created=True)

        # ServerAssignment clone
        server_clone = ZabbixServerAssignment.objects.filter(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk).first()
        self.assertIsNotNone(server_clone)
        self.assertEqual(server_clone.zabbixconfigurationgroup, self.cfg)

        # TemplateAssignment clone
        template_clone = ZabbixTemplateAssignment.objects.filter(zabbixtemplate=self.template, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk).first()
        self.assertIsNotNone(template_clone)
        self.assertEqual(template_clone.zabbixconfigurationgroup, self.cfg)

        # TagAssignment clone
        tag_clone = ZabbixTagAssignment.objects.filter(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk).first()
        self.assertIsNotNone(tag_clone)
        self.assertEqual(tag_clone.zabbixconfigurationgroup, self.cfg)

        # HostgroupAssignment clone
        hg_clone = ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup=self.hostgroup, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk).first()
        self.assertIsNotNone(hg_clone)
        self.assertEqual(hg_clone.zabbixconfigurationgroup, self.cfg)

        # MacroAssignment clone
        macro_clone = ZabbixMacroAssignment.objects.filter(zabbixmacro=self.macro, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk).first()
        self.assertIsNotNone(macro_clone)
        self.assertEqual(macro_clone.zabbixconfigurationgroup, self.cfg)
        self.assertEqual(macro_clone.parent, self.macro_parent)

        # HostInterface clone
        hi_clone = ZabbixHostInterface.objects.filter(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk, parent=self.hostinterface_parent).first()
        self.assertIsNotNone(hi_clone, 'Expected a host interface clone for device')
        self.assertEqual(hi_clone.zabbixconfigurationgroup, self.cfg)
        self.assertEqual(hi_clone.ip, self.devices[0].primary_ip)
        self.assertEqual(hi_clone.interface_type, self.hostinterface_parent.interface_type)
        self.assertEqual(hi_clone.type, self.hostinterface_parent.type)
        self.assertEqual(hi_clone.port, self.hostinterface_parent.port)

    @patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda fn: fn())
    @patch('nbxsync.signals.zabbixconfigurationgroupassignment.transaction.on_commit', side_effect=lambda fn: fn())
    def test_postdelete_deletes_children_for_one_assignment_only(self, *_mocks):
        self._create_all_parent_assignments()

        assignment1 = ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)
        assignment2 = ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[1].pk)

        handle_postsave_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=assignment1, created=True)
        handle_postsave_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=assignment2, created=True)

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

        # Now simulate the post_delete handler by calling it directly
        handle_postdelete_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=assignment1)

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

    def test_postsave_returns_early_when_configgroup_none(self):
        class Dummy:
            pass

        assignment = Dummy()
        assignment.zabbixconfigurationgroup = None

        self.assertEqual(ZabbixServerAssignment.objects.count(), 0)
        self.assertEqual(ZabbixTemplateAssignment.objects.count(), 0)
        self.assertEqual(ZabbixTagAssignment.objects.count(), 0)
        self.assertEqual(ZabbixHostgroupAssignment.objects.count(), 0)
        self.assertEqual(ZabbixMacroAssignment.objects.count(), 0)
        self.assertEqual(ZabbixHostInterface.objects.count(), 0)

        handle_postsave_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=assignment, created=True)

        self.assertEqual(ZabbixServerAssignment.objects.count(), 0)
        self.assertEqual(ZabbixTemplateAssignment.objects.count(), 0)
        self.assertEqual(ZabbixTagAssignment.objects.count(), 0)
        self.assertEqual(ZabbixHostgroupAssignment.objects.count(), 0)
        self.assertEqual(ZabbixMacroAssignment.objects.count(), 0)
        self.assertEqual(ZabbixHostInterface.objects.count(), 0)

    @patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda fn: fn())
    @patch('nbxsync.signals.zabbixconfigurationgroupassignment.transaction.on_commit', side_effect=lambda fn: fn())
    def test_hostinterface_sync_skips_members_without_primary_ip(self, *_mocks):
        hostinterface_parent = ZabbixHostInterface.objects.create(zabbixserver=self.server, type=1, useip=1, interface_type=1, ip=IPAddress.objects.create(address='192.0.2.10/32'), port=10051, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        dev_with_ip = self.devices[0]
        dev_no_ip = create_test_device(name='CfgGroup Dev No IP')

        assignment_with_ip = ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=dev_with_ip.pk)
        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=dev_no_ip.pk)

        handle_postsave_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=assignment_with_ip, created=True)

        self.assertTrue(ZabbixHostInterface.objects.filter(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=dev_with_ip.pk, parent=hostinterface_parent).exists())
        self.assertFalse(ZabbixHostInterface.objects.filter(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=dev_no_ip.pk, parent=hostinterface_parent).exists())

    def test_postdelete_returns_early_when_configgroup_none(self):
        child_server = ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk, zabbixconfigurationgroup=self.cfg)

        class Dummy:
            pass

        assignment = Dummy()
        assignment.zabbixconfigurationgroup = None
        assignment.assigned_object_type = self.device_ct
        assignment.assigned_object_id = self.devices[0].pk

        handle_postdelete_zabbixconfigurationgroupassignment(sender=ZabbixConfigurationGroupAssignment, instance=assignment)

        self.assertTrue(ZabbixServerAssignment.objects.filter(pk=child_server.pk).exists())

    def test_resync_returns_early_when_configgroup_none(self):
        class Dummy:
            pass

        instance = Dummy()
        instance.zabbixconfigurationgroup = None

        self.assertEqual(ZabbixServerAssignment.objects.count(), 0)
        self.assertEqual(ZabbixTemplateAssignment.objects.count(), 0)
        self.assertEqual(ZabbixTagAssignment.objects.count(), 0)
        self.assertEqual(ZabbixHostgroupAssignment.objects.count(), 0)
        self.assertEqual(ZabbixMacroAssignment.objects.count(), 0)
        self.assertEqual(ZabbixHostInterface.objects.count(), 0)

        resync_zabbixconfigurationgroupassignment(instance)

        self.assertEqual(ZabbixServerAssignment.objects.count(), 0)
        self.assertEqual(ZabbixTemplateAssignment.objects.count(), 0)
        self.assertEqual(ZabbixTagAssignment.objects.count(), 0)
        self.assertEqual(ZabbixHostgroupAssignment.objects.count(), 0)
        self.assertEqual(ZabbixMacroAssignment.objects.count(), 0)
        self.assertEqual(ZabbixHostInterface.objects.count(), 0)

    @patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda fn: fn())
    @patch('nbxsync.utils.cfggroup.resync_zabbixconfiggroupassignment.transaction.on_commit', side_effect=lambda fn: fn())
    def test_resync_creates_children_for_all_members(self, *_mocks):
        self._create_all_parent_assignments()

        asn1 = ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)
        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=self.devices[1].pk)

        # Call resync for some instance pointing at this config group
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

    @patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda fn: fn())
    @patch('nbxsync.utils.cfggroup.resync_zabbixconfiggroupassignment.transaction.on_commit', side_effect=lambda fn: fn())
    def test_resync_hostinterface_skips_members_without_primary_ip(self, *_mocks):
        hostinterface_parent = ZabbixHostInterface.objects.create(zabbixserver=self.server, type=1, useip=1, interface_type=1, ip=IPAddress.objects.create(address='192.0.2.20/32'), port=10051, assigned_object_type=self.cfg_ct, assigned_object_id=self.cfg.pk)

        dev_with_ip = self.devices[0]
        dev_no_ip = create_test_device(name='CfgGroup Dev No IP (resync)')

        asn_with_ip = ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=dev_with_ip.pk)
        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.cfg, assigned_object_type=self.device_ct, assigned_object_id=dev_no_ip.pk)

        resync_zabbixconfigurationgroupassignment(asn_with_ip)

        self.assertTrue(ZabbixHostInterface.objects.filter(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=dev_with_ip.pk, parent=hostinterface_parent).exists())
        self.assertFalse(ZabbixHostInterface.objects.filter(zabbixserver=self.server, assigned_object_type=self.device_ct, assigned_object_id=dev_no_ip.pk, parent=hostinterface_parent).exists())
