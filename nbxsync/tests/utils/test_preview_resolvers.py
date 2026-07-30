"""Tests for resolving a representative device per assignment target type.

Each hierarchy level resolves through its own relation. Sharing one resolver
between SiteGroup and Region made a Region assignment preview the device of the
SiteGroup that happened to have the same primary key.
"""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import DeviceType, Manufacturer, Platform, Region, Site, SiteGroup
from utilities.testing import create_test_device
from virtualization.models import Cluster, ClusterType, VirtualMachine

from nbxsync.models import ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixServer
from nbxsync.templatetags.zabbix_preview import zabbix_preview_representative
from nbxsync.utils import preview
from nbxsync.utils.preview import get_representative_device


class PreviewResolverTestCase(TestCase):
    def setUp(self):
        preview._CACHE.clear()
        self.addCleanup(preview._CACHE.clear)
        self.server = ZabbixServer.objects.create(name='Preview Resolver Server')
        self.hostgroup = ZabbixHostgroup.objects.create(name='Groups', value='Groups/{{ object.name }}', zabbixserver=self.server)

    def _assignment(self, target):
        return ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=self.hostgroup,
            assigned_object_type=ContentType.objects.get_for_model(type(target)),
            assigned_object_id=target.pk,
        )

    def test_region_and_sitegroup_resolve_independently(self):
        region = Region.objects.create(name='Region A', slug='region-a')
        sitegroup = SiteGroup.objects.create(name='Group A', slug='group-a')
        region_site = Site.objects.create(name='Region Site', slug='region-site', region=region)
        group_site = Site.objects.create(name='Group Site', slug='group-site', group=sitegroup)
        region_device = create_test_device(name='region-dev', site=region_site)
        group_device = create_test_device(name='group-dev', site=group_site)

        self.assertEqual(get_representative_device(self._assignment(region)), region_device)
        self.assertEqual(get_representative_device(self._assignment(sitegroup)), group_device)

    def test_region_descendants_are_included(self):
        parent = Region.objects.create(name='Parent Region', slug='parent-region')
        child = Region.objects.create(name='Child Region', slug='child-region', parent=parent)
        site = Site.objects.create(name='Child Site', slug='child-site', region=child)
        device = create_test_device(name='child-dev', site=site)

        self.assertEqual(get_representative_device(self._assignment(parent)), device)

    def test_sitegroup_descendants_are_included(self):
        parent = SiteGroup.objects.create(name='Parent Group', slug='parent-group')
        child = SiteGroup.objects.create(name='Child Group', slug='child-group', parent=parent)
        site = Site.objects.create(name='Grouped Site', slug='grouped-site', group=child)
        device = create_test_device(name='grouped-dev', site=site)

        self.assertEqual(get_representative_device(self._assignment(parent)), device)

    def test_region_without_devices_resolves_to_nothing(self):
        region = Region.objects.create(name='Empty Region', slug='empty-region')

        self.assertIsNone(get_representative_device(self._assignment(region)))

    def test_virtual_machine_is_used_when_no_device_exists(self):
        region = Region.objects.create(name='VM Region', slug='vm-region')
        site = Site.objects.create(name='VM Site', slug='vm-site', region=region)
        cluster = Cluster.objects.create(name='VM Cluster', type=ClusterType.objects.create(name='VM Type', slug='vm-type'), scope=site)
        vm = VirtualMachine.objects.create(name='region-vm', cluster=cluster)

        self.assertEqual(get_representative_device(self._assignment(region)), vm)

    def test_device_target_is_returned_unchanged(self):
        device = create_test_device(name='direct-dev')

        self.assertEqual(get_representative_device(self._assignment(device)), device)

    def test_manufacturer_devicetype_and_platform_resolve(self):
        device = create_test_device(name='typed-dev')
        platform = Platform.objects.create(name='Preview Platform', slug='preview-platform')
        device.platform = platform
        device.save()

        self.assertEqual(get_representative_device(self._assignment(device.device_type)), device)
        self.assertEqual(get_representative_device(self._assignment(device.device_type.manufacturer)), device)
        self.assertEqual(get_representative_device(self._assignment(platform)), device)

    def test_cluster_and_clustertype_resolve(self):
        cluster_type = ClusterType.objects.create(name='Cluster Type', slug='cluster-type')
        cluster = Cluster.objects.create(name='Preview Cluster', type=cluster_type)
        vm = VirtualMachine.objects.create(name='cluster-vm', cluster=cluster)

        self.assertEqual(get_representative_device(self._assignment(cluster)), vm)
        self.assertEqual(get_representative_device(self._assignment(cluster_type)), vm)

    def test_unknown_target_type_resolves_to_nothing(self):
        self.assertIsNone(get_representative_device(self._assignment(self.server)))

    def test_missing_target_resolves_to_nothing(self):
        manufacturer = Manufacturer.objects.create(name='Gone', slug='gone')
        assignment = self._assignment(manufacturer)
        manufacturer_pk = manufacturer.pk
        DeviceType.objects.filter(manufacturer=manufacturer).delete()
        manufacturer.delete()
        assignment.assigned_object_id = manufacturer_pk

        self.assertIsNone(get_representative_device(assignment))

    def test_cached_result_expires(self):
        region = Region.objects.create(name='Cached Region', slug='cached-region')
        assignment = self._assignment(region)

        self.assertIsNone(get_representative_device(assignment))

        site = Site.objects.create(name='Late Site', slug='late-site', region=region)
        device = create_test_device(name='late-dev', site=site)
        # Within the TTL the previous answer is reused; expiring it picks up the device.
        self.assertIsNone(get_representative_device(assignment))
        preview._CACHE.clear()

        self.assertEqual(get_representative_device(assignment), device)

    def test_cache_is_bounded(self):
        for index in range(preview._CACHE_MAXSIZE + 5):
            region = Region.objects.create(name=f'Bulk Region {index}', slug=f'bulk-region-{index}')
            get_representative_device(self._assignment(region))

        self.assertLessEqual(len(preview._CACHE), preview._CACHE_MAXSIZE)

    def test_representative_templatetag_discloses_only_inherited_values(self):
        region = Region.objects.create(name='Tag Region', slug='tag-region')
        site = Site.objects.create(name='Tag Site', slug='tag-site', region=region)
        device = create_test_device(name='tag-dev', site=site)

        self.assertEqual(zabbix_preview_representative(self._assignment(region)), str(device))
        self.assertEqual(zabbix_preview_representative(self._assignment(device)), '')

    def test_representative_templatetag_without_a_target(self):
        assignment = self._assignment(Region.objects.create(name='Orphan Region', slug='orphan-region'))
        assignment.assigned_object_id = 9_000_123

        self.assertEqual(zabbix_preview_representative(assignment), '')
