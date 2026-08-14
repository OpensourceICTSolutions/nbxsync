import logging
import re
from functools import lru_cache

from django.core.exceptions import ValidationError
from django.db import models

from netbox.models import NetBoxModel

logger = logging.getLogger(__name__)

__all__ = ('ZabbixTemplateRule',)

# Platform names are short. Keeping the cap low bounds the cost of a careless
# pattern without touching process-global signals (which break RQ job timeouts).
_MAX_MATCH_INPUT = 64
# Role names are capped by NetBox at 100 characters.
_MAX_ROLE_INPUT = 100

# NetBox tag slugs: lowercase alphanumerics, dash, underscore.
_TAG_SLUG = re.compile(r'^[a-z0-9_-]+$')
# Nested quantifiers like (a+)+ / (a*){2,} are the classic ReDoS shape.
_NESTED_QUANTIFIER = re.compile(r'(?<!\\)\([^)]*[+*][^)]*\)[+*{]')


@lru_cache(maxsize=256)
def _compiled_pattern(pattern):
    return re.compile(pattern, re.IGNORECASE)


class ZabbixTemplateRule(NetBoxModel):
    name = models.CharField(max_length=100, blank=False)
    description = models.CharField(max_length=200, blank=True)
    pattern = models.CharField(max_length=500, blank=False, help_text='Case-insensitive regex matched with re.search against the Platform name (not anchored). Use .* as a catch-all when matching on role/tags/manufacturer instead.')
    role_pattern = models.CharField(max_length=500, blank=True, help_text='Optional regex matched against the Device/VM role name (case-insensitive). Empty = any role.')
    require_tags = models.CharField(max_length=200, blank=True, help_text='Optional comma-separated NetBox tag slugs the object must carry (all of them). Empty = tag-independent.')
    manufacturer = models.ForeignKey(
        to='dcim.Manufacturer',
        on_delete=models.PROTECT,
        related_name='zabbixtemplaterules',
        blank=True,
        null=True,
        help_text='Optional. When set, the Device device_type.manufacturer must match. Empty = any manufacturer. Objects without a manufacturer (e.g. VMs) fail closed when this is set. PROTECT prevents deleting a Manufacturer that would silently widen matching rules.',
    )
    zabbixtemplate = models.ForeignKey(to='nbxsync.ZabbixTemplate', on_delete=models.PROTECT, related_name='zabbixtemplaterules')
    zabbixhostgroup = models.ForeignKey(
        to='nbxsync.ZabbixHostgroup',
        on_delete=models.PROTECT,
        related_name='zabbixtemplaterules',
        blank=True,
        null=True,
        help_text='Optional hostgroup assigned when the rule matches. PROTECT prevents deleting a hostgroup that would silently drop this side effect from matching rules.',
    )
    zabbixtag = models.ForeignKey(
        to='nbxsync.ZabbixTag',
        on_delete=models.PROTECT,
        related_name='zabbixtemplaterules',
        blank=True,
        null=True,
        help_text='Optional tag assigned when the rule matches. PROTECT prevents deleting a tag that would silently drop this side effect from matching rules.',
    )
    enabled = models.BooleanField(default=True)
    priority = models.IntegerField(default=100, help_text='Lower value = higher priority')

    class Meta:
        verbose_name = 'Zabbix Template Rule'
        verbose_name_plural = 'Zabbix Template Rules'
        ordering = ('priority', 'name')

    def clean(self):
        super().clean()
        try:
            re.compile(self.pattern)
        except re.error as e:
            raise ValidationError({'pattern': f'Invalid regex: {e}'})

        if self.pattern and _NESTED_QUANTIFIER.search(self.pattern):
            raise ValidationError({'pattern': 'Pattern uses nested quantifiers that can cause catastrophic backtracking. Prefer a simpler expression (for example "Windows" or "Ubuntu|Debian").'})

        if self.role_pattern:
            try:
                re.compile(self.role_pattern)
            except re.error as e:
                raise ValidationError({'role_pattern': f'Invalid regex: {e}'})
            if _NESTED_QUANTIFIER.search(self.role_pattern):
                raise ValidationError({'role_pattern': 'Pattern uses nested quantifiers that can cause catastrophic backtracking. Prefer a simpler expression.'})

        invalid_tags = [slug for slug in self.required_tag_slugs() if not _TAG_SLUG.match(slug)]
        if invalid_tags:
            raise ValidationError({'require_tags': f'Invalid tag slug(s): {", ".join(invalid_tags)}. Use lowercase letters, digits, dash and underscore only.'})

        if self.zabbixhostgroup_id and self.zabbixtemplate_id:
            if self.zabbixhostgroup.zabbixserver_id != self.zabbixtemplate.zabbixserver_id:
                raise ValidationError({'zabbixhostgroup': 'Hostgroup must belong to the same Zabbix server as the template.'})
        # ZabbixTag is server-agnostic in nbxsync (no zabbixserver FK), so no
        # cross-server check applies for zabbixtag.

    def required_tag_slugs(self):
        """Normalized list of required NetBox tag slugs (empty-safe, never raises)."""
        return [slug.strip() for slug in (self.require_tags or '').split(',') if slug.strip()]

    def matches(self, platform_name, *, role_name=None, netbox_tags=None, manufacturer_id=None):  # noqa: C901 — conjunctive criteria ladder reads better flat than split
        """Whether this rule applies to an object.

        Criteria are conjunctive (AND): every configured criterion must match.
        Empty criterion fields are wildcards. A set criterion with no value on
        the object (e.g. role_pattern set but the object has no role, or
        manufacturer set but the object has none) fails closed — the rule
        does not fire.

        Never raises: a rule that cannot be evaluated must not abort a host
        sync, and it must not match either — silently linking the wrong
        template is worse than linking none.
        """
        if not self.enabled:
            return False
        if platform_name is None:
            platform_name = ''
        if len(platform_name) > _MAX_MATCH_INPUT:
            logger.warning('Rule "%s" not evaluated: platform name exceeds %s characters', self.name, _MAX_MATCH_INPUT)
            return False
        try:
            if not _compiled_pattern(self.pattern).search(platform_name):
                return False
        except re.error as err:
            # Patterns are validated on save, but a rule may predate that
            # validation or have been written directly to the database.
            logger.error('Rule "%s" has an invalid pattern "%s": %s', self.name, self.pattern, err)
            return False

        if self.role_pattern:
            role_value = role_name or ''
            if len(role_value) > _MAX_ROLE_INPUT:
                logger.warning('Rule "%s" not evaluated: role name exceeds %s characters', self.name, _MAX_ROLE_INPUT)
                return False
            try:
                if not _compiled_pattern(self.role_pattern).search(role_value):
                    return False
            except re.error as err:
                logger.error('Rule "%s" has an invalid role pattern "%s": %s', self.name, self.role_pattern, err)
                return False

        required = self.required_tag_slugs()
        if required:
            tags = set(netbox_tags or ())
            if not all(slug in tags for slug in required):
                return False

        if self.manufacturer_id is not None:
            # Fail closed: missing manufacturer (VMs, incomplete device_type) must
            # not satisfy a vendor-scoped rule. Compare by PK only — never raise
            # on a missing related object.
            if manufacturer_id is None or manufacturer_id != self.manufacturer_id:
                return False

        return True

    def __str__(self):
        return f'{self.name} ({self.pattern})'
