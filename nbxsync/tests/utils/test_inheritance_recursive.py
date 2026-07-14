from django.test import TestCase

from dcim.models import Site, SiteGroup
from utilities.testing import create_test_device

from nbxsync.models import ZabbixServer, ZabbixServerAssignment
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
        sg = SiteGroup.objects.create(name='Solo', slug='solo')
        ancestors = list(_walk_ancestors(sg))
        self.assertEqual(ancestors, [sg])


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

    def test_root_sitegroup_assignment_resolves_for_deep_hierarchy(self):
        """Assignment on HU (root) is found for a device at HU-DEB-NAG-B (3 levels deep)."""
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.sg_ct, assigned_object_id=self.root_sg.pk)
        result = resolve_inherited_zabbix_assignments(self.device)
        self.assertIn(self.server.pk, result['server_assignments'])

    def test_nearest_ancestor_wins(self):
        """If both HU and HU-DEB-NAG have assignments, the nearest (HU-DEB-NAG) is used."""
        ZabbixServerAssignment.objects.create(zabbixserver=self.server, assigned_object_type=self.sg_ct, assigned_object_id=self.root_sg.pk)
        server2 = ZabbixServer.objects.create(name='Z2', url='http://z2.local', token='t2')
        ZabbixServerAssignment.objects.create(zabbixserver=server2, assigned_object_type=self.sg_ct, assigned_object_id=self.leaf_sg.pk)
        result = resolve_inherited_zabbix_assignments(self.device)
        self.assertIn(self.server.pk, result['server_assignments'])
        self.assertIn(server2.pk, result['server_assignments'])
