from unittest.mock import Mock, patch
from types import SimpleNamespace
from collections import defaultdict

from django.db.models.query import QuerySet
from django.contrib.contenttypes.models import ContentType
from django.test import SimpleTestCase, TestCase

from dcim.models import DeviceType, Manufacturer
from utilities.testing import create_test_device

from nbxsync.models import ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixMacro, ZabbixMacroAssignment, ZabbixServer, ZabbixTag, ZabbixTagAssignment, ZabbixTemplate, ZabbixTemplateAssignment, ZabbixConfigurationGroup, ZabbixConfigurationGroupAssignment
from nbxsync.utils.inheritance import get_assigned_zabbixobjects, resolve_inherited_zabbix_assignments, _merge_direct_and_inherited, _INHERITANCE_MODELS


class ResolveInheritedAssignmentsTestCase(TestCase):
    def setUp(self):
        self.device = create_test_device(name='TestDev')
        self.manufacturer = Manufacturer.objects.get(id=self.device.device_type.manufacturer.id)
        self.device_type = DeviceType.objects.get(id=self.device.device_type.id)
        self.zabbixserver = ZabbixServer.objects.create(name='Zabbix1', url='http://zabbix.local', token='abc123', validate_certs=True)

        # Create related inherited objects
        self.template = ZabbixTemplate.objects.create(name='Template1', zabbixserver=self.zabbixserver, templateid=101)
        self.macro = ZabbixMacro.objects.create(macro='{$ENV}', value='prod', type=0, hostmacroid=201)
        self.tag = ZabbixTag.objects.create(tag='region', value='us-east')
        self.hostgroup = ZabbixHostgroup.objects.create(name='Core', value='core-group', groupid=401, zabbixserver=self.zabbixserver)
        self.configurationgroup = ZabbixConfigurationGroup.objects.create(name='Older Group', description='Created first')

        ct = ContentType.objects.get_for_model(self.device_type)

        ZabbixTemplateAssignment.objects.create(zabbixtemplate=self.template, assigned_object_type=ct, assigned_object_id=self.device_type.pk)
        ZabbixMacroAssignment.objects.create(zabbixmacro=self.macro, assigned_object_type=ct, assigned_object_id=self.device_type.pk, value='inherited')
        ZabbixTagAssignment.objects.create(zabbixtag=self.tag, assigned_object_type=ct, assigned_object_id=self.device_type.pk)
        ZabbixHostgroupAssignment.objects.create(zabbixhostgroup=self.hostgroup, assigned_object_type=ct, assigned_object_id=self.device_type.pk)
        ZabbixConfigurationGroupAssignment.objects.create(zabbixconfigurationgroup=self.configurationgroup, assigned_object_type=ct, assigned_object_id=self.device_type.pk)

    @patch('nbxsync.utils.inheritance.get_plugin_settings')
    def test_resolve_inherited_assignments(self, mock_settings):
        # Patch plugin settings to define inheritance path
        mock_settings.return_value.inheritance_chain = [('device_type',)]

        result = resolve_inherited_zabbix_assignments(self.device)

        self.assertEqual(len(result['templates']), 1)
        self.assertEqual(len(result['macros']), 1)
        self.assertEqual(len(result['tags']), 1)
        self.assertEqual(len(result['hostgroups']), 1)
        self.assertEqual(len(result['configurationgroups']), 1)

        template = list(result['templates'].values())[0]
        macro = list(result['macros'].values())[0]
        tag = list(result['tags'].values())[0]
        group = list(result['hostgroups'].values())[0]
        configurationgroup = list(result['configurationgroups'].values())[0]

        # Ensure inherited_from is set
        self.assertEqual(template._inherited_from, 'Device Type')
        self.assertEqual(macro._inherited_from, 'Device Type')
        self.assertEqual(tag._inherited_from, 'Device Type')
        self.assertEqual(group._inherited_from, 'Device Type')
        self.assertEqual(configurationgroup._inherited_from, 'Device Type')

    @patch('nbxsync.utils.inheritance.get_plugin_settings')
    def test_resolve_path_returns_none(self, mock_settings):
        # Define a bogus inheritance path that will not resolve
        mock_settings.return_value.inheritance_chain = [('nonexistent',)]

        # Create a dummy object with no such attribute
        dummy = Mock(spec=[])
        dummy.__class__.__name__ = 'DummyObject'

        result = resolve_inherited_zabbix_assignments(dummy)

        # Assert that no inherited objects were found
        self.assertEqual(result['templates'], {})
        self.assertEqual(result['macros'], {})
        self.assertEqual(result['tags'], {})
        self.assertEqual(result['hostgroups'], {})
        self.assertEqual(result['configurationgroups'], {})

    @patch('nbxsync.utils.inheritance.get_plugin_settings')
    def test_resolve_path_handles_queryset_first_none(self, mock_settings):
        """
        Covers the branch where resolve_path() encounters a QuerySet or Manager,
        calls .first(), and receives None.
        """
        # Create a dummy object whose attribute simulates a related manager
        dummy_qs = Mock(spec=QuerySet)
        dummy_qs.first.return_value = None  # Simulate empty related set

        dummy_obj = Mock()
        dummy_obj.empty_relation = dummy_qs  # Attribute path target

        # Mock plugin settings with a path leading to our dummy relation
        mock_settings.return_value.inheritance_chain = [('empty_relation',)]

        # Call the function under test — should trigger the two missed lines
        result = resolve_inherited_zabbix_assignments(dummy_obj)

        # Should still return empty dicts since nothing was resolved
        self.assertEqual(result['templates'], {})
        self.assertEqual(result['macros'], {})
        self.assertEqual(result['tags'], {})
        self.assertEqual(result['hostgroups'], {})
        self.assertEqual(result['configurationgroups'], {})

        # Verify .first() was actually called (hitting the missed line)
        dummy_qs.first.assert_called_once()


class MergeDirectAndInheritedTests(SimpleTestCase):
    def test_inherited_duplicate_of_direct_is_skipped(self):
        direct = [SimpleNamespace(zabbixtemplate_id=1, source='direct')]
        inherited = {
            1: SimpleNamespace(zabbixtemplate_id=1, source='inherited-dup'),
            2: SimpleNamespace(zabbixtemplate_id=2, source='inherited-new'),
        }

        result = _merge_direct_and_inherited(direct, inherited, 'zabbixtemplate_id')

        # The direct entry is preserved; the inherited row with id=1 is
        # skipped by the `continue`; the inherited row with id=2 is appended.
        self.assertEqual([obj.source for obj in result], ['direct', 'inherited-new'])

    def test_no_direct_means_all_inherited_flow_through(self):
        # Guards against a future refactor that accidentally short-circuits
        # the whole loop when direct_ids is empty.
        direct = []
        inherited = {1: SimpleNamespace(zabbixtemplate_id=1)}

        result = _merge_direct_and_inherited(direct, inherited, 'zabbixtemplate_id')

        self.assertEqual(len(result), 1)


class ResolveInheritedFirstWriteWinsTests(SimpleTestCase):
    """
    Regression: the `continue` inside `resolve_inherited_zabbix_assignments`
    must reject an assignment whose dedup id was already seen from an
    earlier path. Without it, a later path silently overwrites the
    `_inherited_from` label of the earlier one.
    """

    @patch('nbxsync.utils.inheritance.get_plugin_settings')
    @patch('nbxsync.utils.inheritance._index_assignments')
    @patch('nbxsync.utils.inheritance._resolve_parents')
    def test_second_path_with_duplicate_id_is_skipped(self, mock_resolve_parents, mock_index_assignments, mock_settings):
        # Two resolved paths, both pointing at the same (ct_id, pk) bucket
        # keyed by (99, 1) in the index. Labels differ so we can tell which
        # one won.
        mock_settings.return_value.inheritance_chain = [
            ('device_type',),  # PATH_LABELS -> 'Device Type'
            ('device_type', 'manufacturer'),  # PATH_LABELS -> 'Manufacturer'
        ]

        parent_a = SimpleNamespace(pk=1)
        parent_b = SimpleNamespace(pk=2)
        mock_resolve_parents.return_value = (
            [
                (('device_type',), parent_a, 99),
                (('device_type', 'manufacturer'), parent_b, 99),
            ],
            {99: {1, 2}},
        )

        # For the FIRST assignment model (templates), return an entry at
        # BOTH parent keys with the SAME dedup id. This is the collision
        # that the `continue` protects against. For the remaining four
        # models, return empty dicts.
        dedup_attr = _INHERITANCE_MODELS[0][2]  # 'zabbixtemplate_id'
        shared_dedup_value = 4242

        assignment_from_path_a = SimpleNamespace(**{dedup_attr: shared_dedup_value})
        assignment_from_path_b = SimpleNamespace(**{dedup_attr: shared_dedup_value})

        templates_index = defaultdict(
            list,
            {
                (99, 1): [assignment_from_path_a],  # first path resolves here
                (99, 2): [assignment_from_path_b],  # second path resolves here
            },
        )
        empty_indexes = [defaultdict(list) for _ in _INHERITANCE_MODELS[1:]]
        mock_index_assignments.return_value = [templates_index, *empty_indexes]

        result = resolve_inherited_zabbix_assignments(SimpleNamespace())

        # Exactly one entry — the second was rejected by the `continue`.
        self.assertEqual(len(result['templates']), 1)

        # The surviving entry is the one from path A, so its
        # _inherited_from label is 'Device Type', NOT 'Manufacturer'.
        # If the `continue` were removed, the loop would fall through,
        # set assignment_from_path_b._inherited_from = 'Manufacturer',
        # and overwrite results[0][shared_dedup_value] with it.
        surviving = next(iter(result['templates'].values()))
        self.assertIs(surviving, assignment_from_path_a)
        self.assertEqual(surviving._inherited_from, 'Device Type')

        # And the path-B assignment must NOT have been mutated — the
        # `continue` fires *before* the `assignment._inherited_from = label`
        # line, so it never gets the attribute.
        self.assertFalse(hasattr(assignment_from_path_b, '_inherited_from'))
