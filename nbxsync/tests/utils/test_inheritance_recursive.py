from unittest.mock import Mock

from django.test import TestCase

from dcim.models import DeviceRole, Region, Site, SiteGroup
from utilities.testing import create_test_device

from nbxsync.models import ZabbixProxy, ZabbixServer, ZabbixServerAssignment
from nbxsync.utils.inheritance import _walk_ancestors, resolve_inherited_zabbix_assignments


class WalkAncestorsTestCase(TestCase):
    def test_walk_sitegroup_ancestors(self):
        root = SiteGroup.objects.create(name='HU', slug='hu')
        mid = SiteGroup.objects.create(name='HU-DEB', slug='hu-deb', parent=root)
        leaf = SiteGroup.objects.create(name='HU-DEB-NAG', slug='hu-deb-nag', parent=mid)
        ancestors = list(_walk_ancestors(leaf))
        self.assertEqual(ancestors, [leaf, mid, root])

    def test_walk_with_none(self):
        self.assertEqual(list(_walk_ancestors(None)), [])

    def test_cycle_detected(self):
        first = Mock(name='first')
        second = Mock(name='second')
        first.parent = second
        second.parent = first

        self.assertEqual(list(_walk_ancestors(first)), [first, second])

    def test_walk_region_ancestors(self):
        root = Region.objects.create(name='Europe', slug='europe')
        child = Region.objects.create(name='Hungary', slug='hu', parent=root)
        leaf = Region.objects.create(name='Budapest', slug='bp', parent=child)
        ancestors = list(_walk_ancestors(leaf))
        self.assertEqual(ancestors, [leaf, child, root])

    def test_walk_devicerole_ancestors(self):
        root = DeviceRole.objects.create(name='Network', slug='network')
        child = DeviceRole.objects.create(name='Switch', slug='switch', parent=root)
        leaf = DeviceRole.objects.create(name='Core Switch', slug='core-switch', parent=child)
        ancestors = list(_walk_ancestors(leaf))
        self.assertEqual(ancestors, [leaf, child, root])


class RecursiveInheritanceTestCase(TestCase):
    def setUp(self):
        self.server = ZabbixServer.objects.create(name='Zabbix', url='http://zabbix.local', token='t')
        self.root_sg = SiteGroup.objects.create(name='HU', slug='hu')
        self.mid_sg = SiteGroup.objects.create(name='HU-DEB', slug='hu-deb', parent=self.root_sg)
        self.leaf_sg = SiteGroup.objects.create(name='HU-DEB-NAG', slug='hu-deb-nag', parent=self.mid_sg)
        self.site = Site.objects.create(name='HU-DEB-NAG-B', slug='hu-deb-nag-b', group=self.leaf_sg)
        self.device = create_test_device(name='Dev-at-HU', site=self.site)
        from django.contrib.contenttypes.models import ContentType

        self.sg_ct = ContentType.objects.get_for_model(SiteGroup)
        self.region_ct = ContentType.objects.get_for_model(Region)
        self.role_ct = ContentType.objects.get_for_model(DeviceRole)

    def test_root_sitegroup_assignment_resolves_for_deep_hierarchy(self):
        """Assignment on HU (root) is found for a device at HU-DEB-NAG-B (3 levels deep)."""
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.sg_ct, assigned_object_id=self.root_sg.pk)
        result = resolve_inherited_zabbix_assignments(self.device)
        self.assertIn(self.server.pk, result['server_assignments'])
        assignment = result['server_assignments'][self.server.pk]
        self.assertEqual(assignment._inherited_from, 'Site Group: HU')

    def test_nearest_ancestor_wins(self):
        """The nearest assignment wins when ancestors target the same server."""
        root_proxy = ZabbixProxy.objects.create(
            name='Root Proxy', zabbixserver=self.server, local_address='192.0.2.10', operating_mode=0
        )
        leaf_proxy = ZabbixProxy.objects.create(
            name='Leaf Proxy', zabbixserver=self.server, local_address='192.0.2.11', operating_mode=0
        )
        ZabbixServerAssignment.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.sg_ct,
            assigned_object_id=self.root_sg.pk,
            zabbixproxy=root_proxy,
        )
        leaf_assignment = ZabbixServerAssignment.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.sg_ct,
            assigned_object_id=self.leaf_sg.pk,
            zabbixproxy=leaf_proxy,
        )

        result = resolve_inherited_zabbix_assignments(self.device)

        self.assertEqual(result['server_assignments'][self.server.pk], leaf_assignment)
        self.assertEqual(result['server_assignments'][self.server.pk].zabbixproxy, leaf_proxy)

    def test_region_parent_assignment_resolves_for_deep_hierarchy(self):
        """Assignment on a root Region propagates down a multi-level Region tree."""
        root_region = Region.objects.create(name='Europe', slug='europe')
        mid_region = Region.objects.create(name='Hungary', slug='hu', parent=root_region)
        leaf_region = Region.objects.create(name='Budapest', slug='bp', parent=mid_region)
        region_site = Site.objects.create(name='BP-DC', slug='bp-dc', region=leaf_region)
        device = create_test_device(name='Dev-at-BP', site=region_site)
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.region_ct, assigned_object_id=root_region.pk)
        result = resolve_inherited_zabbix_assignments(device)
        self.assertIn(self.server.pk, result['server_assignments'])

    def test_devicerole_parent_assignment_resolves_for_deep_hierarchy(self):
        """Assignment on a parent DeviceRole propagates down a multi-level Role tree."""
        root_role = DeviceRole.objects.create(name='Network', slug='network')
        mid_role = DeviceRole.objects.create(name='Switch', slug='switch', parent=root_role)
        leaf_role = DeviceRole.objects.create(name='Core Switch', slug='core-switch', parent=mid_role)
        device = create_test_device(name='Dev-Core-Switch')
        device.role = leaf_role
        device.save(update_fields=['role'])
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.role_ct, assigned_object_id=root_role.pk)
        result = resolve_inherited_zabbix_assignments(device)
        self.assertIn(self.server.pk, result['server_assignments'])
