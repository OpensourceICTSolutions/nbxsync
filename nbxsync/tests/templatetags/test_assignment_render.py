"""Tests for assignment-target Jinja rendering (device-shaped wrap).

Device-context templates like ``Roles/{{ object.role.name }}`` must resolve
when assigned to a DeviceRole without borrowing a descendant Device. SiteGroup
assignments that need a per-device role cannot resolve to one Value — the UI
shows the raw template; sync still renders per Device/VM.
"""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dcim.models import Device, DeviceRole, Site, SiteGroup
from utilities.testing import create_test_device

from nbxsync.models import ZabbixHostgroup, ZabbixHostgroupAssignment, ZabbixServer, ZabbixTag, ZabbixTagAssignment
from nbxsync.templatetags.zabbix_hostgroups import render_zabbix_hostgroup_assignment
from nbxsync.templatetags.zabbix_tags import render_zabbix_tag_assignment
from nbxsync.jinja_context import related_template_context, wrap_assignment_object


def _make_device(name, role=None, site=None):
    device = create_test_device(name=name, site=site)
    if role is not None:
        device.role = role
        device.save()
    return device


class AssignmentRenderWrapTestCase(TestCase):
    def test_devicerole_exposes_role_and_name(self):
        role = DeviceRole.objects.create(name='Switch Access', slug='sw-acc-wrap')
        wrapped = wrap_assignment_object(role)
        self.assertIs(wrapped.role, role)
        self.assertEqual(wrapped.name, 'Switch Access')

    def test_site_exposes_site(self):
        site = Site.objects.create(name='CH-SITE', slug='ch-site-wrap')
        wrapped = wrap_assignment_object(site)
        self.assertIs(wrapped.site, site)

    def test_sitegroup_left_unchanged(self):
        group = SiteGroup.objects.create(name='CH', slug='ch-wrap')
        self.assertIs(wrap_assignment_object(group), group)

    def test_device_left_unchanged(self):
        device = _make_device(name='wrap-dev')
        self.assertIs(wrap_assignment_object(device), device)


class HostgroupAssignmentRenderTestCase(TestCase):
    def setUp(self):
        self.zabbixserver = ZabbixServer.objects.create(name='Render Fix Server')

    def test_devicerole_roles_template_resolves(self):
        """Roles/{{ object.role.name }} on DeviceRole → Roles/<that role>."""
        role = DeviceRole.objects.create(name='Network Device', slug='network-device')
        hg = ZabbixHostgroup.objects.create(
            name='Roles',
            value='Roles/{{ object.role.name }}',
            zabbixserver=self.zabbixserver,
        )
        ct = ContentType.objects.get_for_model(DeviceRole)
        assignment = ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=hg,
            assigned_object_type=ct,
            assigned_object_id=role.id,
        )

        output, ok = assignment.render()
        self.assertTrue(ok)
        self.assertEqual(output, 'Roles/Network Device')
        self.assertEqual(render_zabbix_hostgroup_assignment({}, assignment), 'Roles/Network Device')

    def test_sitegroup_roles_shows_template_not_sample(self):
        """Roles Jinja on SiteGroup cannot resolve to one role — show template."""
        parent = SiteGroup.objects.create(name='CH', slug='ch-render')
        site = Site.objects.create(name='CH-SITE', slug='ch-site-render', group=parent)
        role_sw = DeviceRole.objects.create(name='Switch Access', slug='sw-acc-render')
        role_fw = DeviceRole.objects.create(name='Firewall', slug='fw-render')
        _make_device(name='ch-sw-1', role=role_sw, site=site)
        _make_device(name='ch-fw-1', role=role_fw, site=site)

        hg = ZabbixHostgroup.objects.create(
            name='Roles',
            value='Roles/{{ object.role.name }}',
            zabbixserver=self.zabbixserver,
        )
        ct = ContentType.objects.get_for_model(SiteGroup)
        assignment = ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=hg,
            assigned_object_type=ct,
            assigned_object_id=parent.id,
        )

        output, ok = assignment.render()
        self.assertFalse(ok)
        self.assertEqual(
            render_zabbix_hostgroup_assignment({}, assignment),
            'Roles/{{ object.role.name }}',
        )

        # Sync path still renders per device.
        synced = {assignment.render(object=d)[0] for d in Device.objects.filter(site=site)}
        self.assertEqual(synced, {'Roles/Switch Access', 'Roles/Firewall'})

    def test_site_sites_template_resolves(self):
        group = SiteGroup.objects.create(name='CH', slug='ch-sites')
        site = Site.objects.create(name='CH-STA-L44', slug='ch-sta-l44', group=group)
        hg = ZabbixHostgroup.objects.create(
            name='Sites',
            value='Sites/{{ object.site.group.name }}/{{ object.site.name }}',
            zabbixserver=self.zabbixserver,
        )
        ct = ContentType.objects.get_for_model(Site)
        assignment = ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=hg,
            assigned_object_type=ct,
            assigned_object_id=site.id,
        )

        output, ok = assignment.render()
        self.assertTrue(ok)
        self.assertEqual(output, 'Sites/CH/CH-STA-L44')

    def test_explicit_object_overrides_wrap(self):
        role = DeviceRole.objects.create(name='Override Role', slug='override-role')
        hg = ZabbixHostgroup.objects.create(
            name='Roles',
            value='Roles/{{ object.role.name }}',
            zabbixserver=self.zabbixserver,
        )
        ct = ContentType.objects.get_for_model(DeviceRole)
        assignment = ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=hg,
            assigned_object_type=ct,
            assigned_object_id=role.id,
        )

        other_role = DeviceRole.objects.create(name='Other Role', slug='other-role')
        explicit_device = _make_device(name='explicit-dev', role=other_role)

        rendered = render_zabbix_hostgroup_assignment({}, assignment, object=explicit_device)
        self.assertEqual(rendered, 'Roles/Other Role')

    def test_static_value_passes_through(self):
        hg = ZabbixHostgroup.objects.create(
            name='Managed',
            value='Managed/nbxSync',
            zabbixserver=self.zabbixserver,
        )
        role = DeviceRole.objects.create(name='Any Role', slug='any-role')
        ct = ContentType.objects.get_for_model(DeviceRole)
        assignment = ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=hg,
            assigned_object_type=ct,
            assigned_object_id=role.id,
        )

        self.assertEqual(render_zabbix_hostgroup_assignment({}, assignment), 'Managed/nbxSync')


class TagAssignmentRenderTestCase(TestCase):
    def setUp(self):
        self.zabbixserver = ZabbixServer.objects.create(name='Tag Render Server')

    def test_devicerole_tag_resolves(self):
        role = DeviceRole.objects.create(name='Switch Core', slug='switch-core')
        tag = ZabbixTag.objects.create(
            name='owner',
            tag='owner',
            value='{{ object.role.name }}',
        )
        ct = ContentType.objects.get_for_model(DeviceRole)
        assignment = ZabbixTagAssignment.objects.create(
            zabbixtag=tag,
            assigned_object_type=ct,
            assigned_object_id=role.id,
        )

        self.assertEqual(render_zabbix_tag_assignment({}, assignment), 'Switch Core')

    def test_sitegroup_tag_shows_template(self):
        group = SiteGroup.objects.create(name='HU', slug='hu-tag')
        tag = ZabbixTag.objects.create(
            name='owner',
            tag='owner',
            value='{{ object.role.name }}',
        )
        ct = ContentType.objects.get_for_model(SiteGroup)
        assignment = ZabbixTagAssignment.objects.create(
            zabbixtag=tag,
            assigned_object_type=ct,
            assigned_object_id=group.id,
        )

        self.assertEqual(render_zabbix_tag_assignment({}, assignment), '{{ object.role.name }}')


class RelatedTemplateContextTestCase(TestCase):
    """#102 shorthand aliases follow the render object, not the assignment row."""

    def setUp(self):
        self.zabbixserver = ZabbixServer.objects.create(name='Related Ctx Server')
        self.device = _make_device(name='related-dev')

    def test_device_context_exposes_aliases(self):
        context = related_template_context(self.device)
        self.assertIs(context['device'], self.device)
        self.assertEqual(context['site'], self.device.site)
        self.assertEqual(context['role'], self.device.role)
        self.assertEqual(context['device_type'], self.device.device_type)
        self.assertEqual(context['manufacturer'], self.device.device_type.manufacturer)

    def test_site_wrap_exposes_site_but_not_device(self):
        site = Site.objects.create(name='Alias Site', slug='alias-site')
        context = related_template_context(wrap_assignment_object(site))
        self.assertIs(context['site'], site)
        self.assertNotIn('device', context)

    def test_hostgroup_render_uses_site_and_device_aliases(self):
        hg = ZabbixHostgroup.objects.create(
            name='Sites',
            value='{{ site.name }}/{{ device.name }}',
            zabbixserver=self.zabbixserver,
        )
        ct = ContentType.objects.get_for_model(Device)
        assignment = ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=hg,
            assigned_object_type=ct,
            assigned_object_id=self.device.id,
        )
        output, ok = assignment.render()
        self.assertTrue(ok)
        self.assertEqual(output, f'{self.device.site.name}/{self.device.name}')

    def test_inherited_assignment_aliases_follow_sync_host_not_role(self):
        """A Role-level template rendered with object=device must use the device."""
        assigned_role = DeviceRole.objects.create(name='Assigned Role', slug='assigned-role-alias')
        host_role = DeviceRole.objects.create(name='Host Role', slug='host-role-alias')
        host = _make_device(name='alias-host', role=host_role)
        hg = ZabbixHostgroup.objects.create(
            name='Roles',
            value='{{ role.name }}/{{ device.name }}',
            zabbixserver=self.zabbixserver,
        )
        ct = ContentType.objects.get_for_model(DeviceRole)
        assignment = ZabbixHostgroupAssignment.objects.create(
            zabbixhostgroup=hg,
            assigned_object_type=ct,
            assigned_object_id=assigned_role.id,
        )

        # Role preview has `role` but not `device` — do not pretend the Role is a Device.
        preview, preview_ok = assignment.render()
        self.assertFalse(preview_ok)

        synced, synced_ok = assignment.render(object=host)
        self.assertTrue(synced_ok)
        self.assertEqual(synced, f'{host_role.name}/{host.name}')

    def test_tag_render_related_fields(self):
        tag = ZabbixTag.objects.create(
            name='hw',
            tag='hw',
            value='{{ site.name }} - {{ device_type.model }} - {{ manufacturer.name }}',
        )
        ct = ContentType.objects.get_for_model(Device)
        assignment = ZabbixTagAssignment.objects.create(
            zabbixtag=tag,
            assigned_object_type=ct,
            assigned_object_id=self.device.id,
        )
        self.assertEqual(
            render_zabbix_tag_assignment({}, assignment),
            f'{self.device.site.name} - {self.device.device_type.model} - {self.device.device_type.manufacturer.name}',
        )
