from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.test import TestCase

from dcim.models import Device
from utilities.testing import create_test_device

from nbxsync.models import ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment, ZabbixTag, ZabbixTagAssignment
from nbxsync.utils.cfggroup.helpers import get_configgroup_ct_id, is_configgroup_assignment, iter_configgroup_members, build_defaults_from_instance, propagate_group_assignment, delete_group_clones


class ConfigGroupUtilsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cfg = ZabbixConfigurationGroup.objects.create(name='ConfigGroup A', description='Test configuration group')

        cls.devices = [
            create_test_device(name='CG Device 1'),
            create_test_device(name='CG Device 2'),
        ]
        cls.device_ct = ContentType.objects.get_for_model(Device)

        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=cls.cfg, assigned_object_type=cls.device_ct, assigned_object_id=cls.devices[0].pk)
        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=cls.cfg, assigned_object_type=cls.device_ct, assigned_object_id=cls.devices[1].pk)

        cls.tag = ZabbixTag.objects.create(name='Env', tag='env', value='{{ object.name }}')

    def test_get_configgroup_ct_id_caches_content_type(self):
        # Clear cache if present
        if hasattr(get_configgroup_ct_id, '_ct_id'):
            delattr(get_configgroup_ct_id, '_ct_id')

        with patch('nbxsync.utils.cfggroup.helpers.ContentType.objects.get_for_model', wraps=ContentType.objects.get_for_model) as mocked_get_for_model:
            first = get_configgroup_ct_id()
            second = get_configgroup_ct_id()

        self.assertEqual(first, second)

        mocked_get_for_model.assert_called_once_with(ZabbixConfigurationGroup)

    def test_is_configgroup_assignment_true_for_cfg_assignment(self):
        cfg_ct = ContentType.objects.get_for_model(ZabbixConfigurationGroup)
        assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=cfg_ct, assigned_object_id=self.cfg.pk)

        self.assertTrue(is_configgroup_assignment(assignment))

    def test_is_configgroup_assignment_false_for_other_assignment(self):
        assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk)

        self.assertFalse(is_configgroup_assignment(assignment))

    def test_iter_configgroup_members_returns_all_group_assignments(self):
        cfg_ct = ContentType.objects.get_for_model(ZabbixConfigurationGroup)

        cfg_assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=cfg_ct, assigned_object_id=self.cfg.pk)

        members_qs = iter_configgroup_members(cfg_assignment)
        members = list(members_qs)

        self.assertEqual(len(members), 2)
        for member in members:
            self.assertIsInstance(member, ZabbixConfigurationGroupAssignment)
            self.assertEqual(member.zabbixconfigurationgroup, self.cfg)

    def test_build_defaults_from_instance_handles_fk_and_exclude_and_extra(self):
        cfg_ct = ContentType.objects.get_for_model(ZabbixConfigurationGroup)
        base = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=cfg_ct, assigned_object_id=self.cfg.pk)

        defaults = build_defaults_from_instance(base, exclude=frozenset({'id', 'assigned_object_id'}), extra={'extra_key': 'extra_value'})

        self.assertIn('zabbixtag_id', defaults)
        self.assertEqual(defaults['zabbixtag_id'], self.tag.pk)

        self.assertNotIn('id', defaults)
        self.assertNotIn('assigned_object_id', defaults)

        self.assertIn('assigned_object_type_id', defaults)

        self.assertIn('extra_key', defaults)
        self.assertEqual(defaults['extra_key'], 'extra_value')

    def test_propagate_group_assignment_creates_clones_for_each_member(self):
        cfg_ct = ContentType.objects.get_for_model(ZabbixConfigurationGroup)

        base_assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=cfg_ct, assigned_object_id=self.cfg.pk)

        def lookup_factory(source, assigned):
            return {
                'zabbixtag': source.zabbixtag,
                'assigned_object_type': assigned.assigned_object_type,
                'assigned_object_id': assigned.assigned_object_id,
            }

        with patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda func: func()):
            propagate_group_assignment(instance=base_assignment, model=ZabbixTagAssignment, lookup_factory=lookup_factory, default_exclude=frozenset({'id', 'assigned_object_type', 'assigned_object_id'}), defaults_extra=None)

        for device in self.devices:
            self.assertTrue(
                ZabbixTagAssignment.objects.filter(
                    zabbixtag=self.tag,
                    assigned_object_type=self.device_ct,
                    assigned_object_id=device.pk,
                    zabbixconfigurationgroup=self.cfg,
                ).exists(),
                f'Expected propagated tag assignment for {device}',
            )

    def test_propagate_group_assignment_respects_existing_null_group(self):
        cfg_ct = ContentType.objects.get_for_model(ZabbixConfigurationGroup)

        base_assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=cfg_ct, assigned_object_id=self.cfg.pk)
        existing = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=self.devices[0].pk, zabbixconfigurationgroup=None)

        def lookup_factory(source, assigned):
            return {
                'zabbixtag': source.zabbixtag,
                'assigned_object_type': assigned.assigned_object_type,
                'assigned_object_id': assigned.assigned_object_id,
            }

        with patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda func: func()):
            propagate_group_assignment(
                instance=base_assignment,
                model=ZabbixTagAssignment,
                lookup_factory=lookup_factory,
                default_exclude=frozenset({'id', 'assigned_object_type', 'assigned_object_id'}),
                defaults_extra=None,
            )

        existing.refresh_from_db()
        self.assertIsNone(existing.zabbixconfigurationgroup)

        self.assertTrue(
            ZabbixTagAssignment.objects.filter(
                zabbixtag=self.tag,
                assigned_object_type=self.device_ct,
                assigned_object_id=self.devices[1].pk,
                zabbixconfigurationgroup=self.cfg,
            ).exists()
        )

    def test_propagate_group_assignment_integrityerror_falls_back_to_update(self):
        class DummyQS:
            def __init__(self):
                self.update_calls = []
                self.first_called = False

            def first(self):
                self.first_called = True
                return None

            def update(self, **kwargs):
                self.update_calls.append(kwargs)

        class DummyManager:
            def __init__(self):
                self.qs = DummyQS()
                self.filter_calls = []
                self.update_or_create_calls = []

            def filter(self, **lookup):
                self.filter_calls.append(lookup)
                return self.qs

            def update_or_create(self, **kwargs):
                # Simulate IntegrityError on update_or_create
                self.update_or_create_calls.append(kwargs)
                raise IntegrityError('duplicate')

        class DummyModel:
            objects = DummyManager()

        class DummyInstance:
            def __init__(self, cfg):
                self.assigned_object = cfg

        instance = DummyInstance(self.cfg)
        assigned = object()

        def lookup_factory(src, assigned_obj):
            self.assertIs(src, instance)
            self.assertIs(assigned_obj, assigned)
            return {'key': 'value'}

        with (
            patch('nbxsync.utils.cfggroup.helpers.iter_configgroup_members', return_value=[assigned]),
            patch('nbxsync.utils.cfggroup.helpers.build_defaults_from_instance', return_value={'foo': 'bar'}),
            patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda func: func()),
        ):
            propagate_group_assignment(instance=instance, model=DummyModel, lookup_factory=lookup_factory, default_exclude=frozenset(), defaults_extra={'extra': True})

        self.assertEqual(len(DummyModel.objects.update_or_create_calls), 1)
        self.assertEqual(len(DummyModel.objects.qs.update_calls), 1)
        self.assertEqual(DummyModel.objects.qs.update_calls[0], {'foo': 'bar'})

    def test_delete_group_clones_deletes_all_clones_for_group(self):
        cfg_ct = ContentType.objects.get_for_model(ZabbixConfigurationGroup)

        base_assignment = ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=cfg_ct, assigned_object_id=self.cfg.pk, zabbixconfigurationgroup=self.cfg)

        for device in self.devices:
            ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=self.device_ct, assigned_object_id=device.pk, zabbixconfigurationgroup=self.cfg)

        def lookup_factory(source, assigned):
            return {'pk': assigned.pk}

        with patch('nbxsync.utils.cfggroup.helpers.transaction.on_commit', side_effect=lambda func: func()):
            delete_group_clones(instance=base_assignment, model=ZabbixTagAssignment, lookup_factory=lookup_factory)

        self.assertFalse(ZabbixTagAssignment.objects.filter(zabbixconfigurationgroup=self.cfg).exists())
