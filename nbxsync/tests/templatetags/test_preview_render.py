"""Tests for the representative-device preview rendering.

These cover the regression that motivated the fix: a hostgroup/tag
assignment made against a non-Device target (DeviceRole, SiteGroup, ...)
with a template that traverses device-level attributes (``object.role.name``,
``object.site.group.name``) used to leak a raw Jinja2 UndefinedError into
the NetBox UI. The template tag now substitutes a representative Device/VM
so the preview renders the same value the sync engine produces.
"""
from dcim.models import Device, DeviceRole, Site, SiteGroup
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from nbxsync.models import ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixServer, ZabbixTag, ZabbixTagAssignment
from nbxsync.templatetags.zabbix_hostgroups import (
    render_zabbix_hostgroup_assignment,
)
from nbxsync.templatetags.zabbix_tags import render_zabbix_tag_assignment
from nbxsync.utils.preview import get_representative_device
from utilities.testing import create_test_device


class RepresentativeDeviceTestCase(TestCase):
    """Direct tests for the representative-device resolver."""

    def setUp(self):
        self.zabbixserver = ZabbixServer.objects.create(
            name='Preview Test Server'
        )

    def test_devicerole_returns_matching_device(self):
        """A DeviceRole assignment resolves to the first device with that role."""
        role = DeviceRole.objects.create(
            name='Preview Role', slug='preview-role'
        )
        create_test_device(name='dev-1', role=role)

        hg = ZabbixHostgroup.objects.create(
            name='Roles', value='Roles/{{ object.role.name }}',
            zabbixserver=self.zabbixserver,
        )
        ct = ContentType.objects.get_for_model(DeviceRole)
        assignment = ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=hg,
            assigned_object_type=ct, assigned_object_id=role.id,
        )

        rep = get_representative_device(assignment)
        self.assertIsNotNone(rep)
        self.assertEqual(rep.role_id, role.id)

    def test_sitegroup_recursive_returns_descendant_device(self):
        """Top-level SiteGroup with no direct sites resolves via descendant."""
        parent = SiteGroup.objects.create(
            name='COUNTRY', slug='country'
        )
        child = SiteGroup.objects.create(
            name='COUNTRY-STA', slug='country-sta', parent=parent
        )
        site = Site.objects.create(name='COUNTRY-STA-L26', slug='l26', group=child)
        create_test_device(name='dev-site-1', site=site)

        hg = ZabbixHostgroup.objects.create(
            name='Sites',
            value='Sites/{{ object.site.group.name }}/{{ object.site.name }}',
            zabbixserver=self.zabbixserver,
        )
        ct = ContentType.objects.get_for_model(SiteGroup)
        assignment = ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=hg,
            assigned_object_type=ct, assigned_object_id=parent.id,
        )

        rep = get_representative_device(assignment)
        self.assertIsNotNone(rep)
        self.assertEqual(rep.site_id, site.id)

    def test_empty_devicerole_returns_none(self):
        """A DeviceRole with no matching devices resolves to None (no error)."""
        role = DeviceRole.objects.create(
            name='Empty Role', slug='empty-role'
        )
        hg = ZabbixHostgroup.objects.create(
            name='Roles', value='Roles/{{ object.role.name }}',
            zabbixserver=self.zabbixserver,
        )
        ct = ContentType.objects.get_for_model(DeviceRole)
        assignment = ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=hg,
            assigned_object_type=ct, assigned_object_id=role.id,
        )

        rep = get_representative_device(assignment)
        self.assertIsNone(rep)

    def test_direct_device_assignment_returns_target(self):
        """A Device-targeted assignment returns the Device itself."""
        device = create_test_device(name='direct-dev')
        hg = ZabbixHostgroup.objects.create(
            name='Direct', value='{{ object.name }}',
            zabbixserver=self.zabbixserver,
        )
        ct = ContentType.objects.get_for_model(Device)
        assignment = ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=hg,
            assigned_object_type=ct, assigned_object_id=device.id,
        )

        rep = get_representative_device(assignment)
        self.assertIs(rep, device)


class HostgroupPreviewRenderTestCase(TestCase):
    """End-to-end tests for the render_zabbix_hostgroup_assignment tag."""

    def setUp(self):
        self.zabbixserver = ZabbixServer.objects.create(
            name='Preview Tag Test Server'
        )

    def test_devicerole_template_renders_cleanly(self):
        """Roles/{{ object.role.name }} on a DeviceRole renders as Roles/<role>."""
        role = DeviceRole.objects.create(
            name='Network Device', slug='network-device'
        )
        create_test_device(name='netdev-1', role=role)

        hg = ZabbixHostgroup.objects.create(
            name='Roles', value='Roles/{{ object.role.name }}',
            zabbixserver=self.zabbixserver,
        )
        ct = ContentType.objects.get_for_model(DeviceRole)
        assignment = ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=hg,
            assigned_object_type=ct, assigned_object_id=role.id,
        )

        # No request context needed — the tag falls back to the representative.
        rendered = render_zabbix_hostgroup_assignment({}, assignment)
        self.assertEqual(rendered, 'Roles/Network Device')

    def test_empty_devicerole_returns_empty_string(self):
        """When no representative exists, the tag returns '' (no error leak)."""
        role = DeviceRole.objects.create(
            name='Ghost Role', slug='ghost-role'
        )
        hg = ZabbixHostgroup.objects.create(
            name='Roles', value='Roles/{{ object.role.name }}',
            zabbixserver=self.zabbixserver,
        )
        ct = ContentType.objects.get_for_model(DeviceRole)
        assignment = ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=hg,
            assigned_object_type=ct, assigned_object_id=role.id,
        )

        rendered = render_zabbix_hostgroup_assignment({}, assignment)
        self.assertEqual(rendered, '')
        # Critically: no raw Python error string leaks into the UI.
        self.assertNotIn('Undefined variable', rendered)
        self.assertNotIn('has no attribute', rendered)

    def test_static_value_passes_through_unchanged(self):
        """A static (non-Jinja2) value renders as itself with no lookup."""
        hg = ZabbixHostgroup.objects.create(
            name='Managed', value='Managed/nbxSync',
            zabbixserver=self.zabbixserver,
        )
        role = DeviceRole.objects.create(
            name='Any Role', slug='any-role'
        )
        ct = ContentType.objects.get_for_model(DeviceRole)
        assignment = ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=hg,
            assigned_object_type=ct, assigned_object_id=role.id,
        )

        rendered = render_zabbix_hostgroup_assignment({}, assignment)
        self.assertEqual(rendered, 'Managed/nbxSync')

    def test_explicit_object_overrides_representative(self):
        """When the caller passes object=, the representative is NOT consulted.

        This protects the sync-engine path (which passes object=Device
        explicitly) from being silently overridden by an unrelated
        representative lookup.
        """
        role = DeviceRole.objects.create(
            name='Override Role', slug='override-role'
        )
        # Representative would resolve to this device, but it must NOT be used.
        create_test_device(name='rep-dev', role=role)

        hg = ZabbixHostgroup.objects.create(
            name='Roles', value='Roles/{{ object.role.name }}',
            zabbixserver=self.zabbixserver,
        )
        ct = ContentType.objects.get_for_model(DeviceRole)
        assignment = ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=hg,
            assigned_object_type=ct, assigned_object_id=role.id,
        )

        # Caller supplies an explicit Device as object=.
        other_role = DeviceRole.objects.create(
            name='Other Role', slug='other-role'
        )
        explicit_device = create_test_device(
            name='explicit-dev', role=other_role
        )

        rendered = render_zabbix_hostgroup_assignment(
            {}, assignment, object=explicit_device
        )
        # Uses the explicit device's role, NOT the representative's.
        self.assertEqual(rendered, 'Roles/Other Role')


class TagPreviewRenderTestCase(TestCase):
    """End-to-end tests for the render_zabbix_tag_assignment tag."""

    def setUp(self):
        self.zabbixserver = ZabbixServer.objects.create(
            name='Tag Preview Test Server'
        )

    def test_devicerole_template_renders_cleanly(self):
        """owner={{ object.role.name }} on a DeviceRole renders cleanly."""
        role = DeviceRole.objects.create(
            name='Switch Core', slug='switch-core'
        )
        create_test_device(name='sw-1', role=role)

        tag = ZabbixTag.objects.create(
            name='owner', tag='owner', value='{{ object.role.name }}',
        )
        ct = ContentType.objects.get_for_model(DeviceRole)
        assignment = ZabbixTagAssignment.objects.create(
            zabbixtag=tag,
            assigned_object_type=ct, assigned_object_id=role.id,
        )

        rendered = render_zabbix_tag_assignment({}, assignment)
        self.assertEqual(rendered, 'Switch Core')

    def test_no_representative_returns_empty_string(self):
        """No matching device → empty string, no error leak."""
        role = DeviceRole.objects.create(
            name='Empty Tag Role', slug='empty-tag-role'
        )
        tag = ZabbixTag.objects.create(
            name='owner', tag='owner', value='{{ object.role.name }}',
        )
        ct = ContentType.objects.get_for_model(DeviceRole)
        assignment = ZabbixTagAssignment.objects.create(
            zabbixtag=tag,
            assigned_object_type=ct, assigned_object_id=role.id,
        )

        rendered = render_zabbix_tag_assignment({}, assignment)
        self.assertEqual(rendered, '')
        self.assertNotIn('Undefined variable', rendered)
