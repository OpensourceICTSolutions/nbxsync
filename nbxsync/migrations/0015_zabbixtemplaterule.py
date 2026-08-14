import django.db.models.deletion
import taggit.managers
from django.db import migrations, models

import utilities.json


class Migration(migrations.Migration):
    """ZabbixTemplateRule with compound criteria and optional hostgroup/tag (squashed)."""

    dependencies = [
        ('extras', '0122_charfield_null_choices'),
        ('nbxsync', '0014_tag_assignment_targets'),
    ]

    operations = [
        migrations.CreateModel(
            name='ZabbixTemplateRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ('name', models.CharField(max_length=100)),
                ('description', models.CharField(blank=True, max_length=200)),
                ('pattern', models.CharField(max_length=500)),
                ('role_pattern', models.CharField(blank=True, max_length=500)),
                ('require_tags', models.CharField(blank=True, max_length=200)),
                ('enabled', models.BooleanField(default=True)),
                ('priority', models.IntegerField(default=100)),
                (
                    'manufacturer',
                    models.ForeignKey(
                        blank=True,
                        help_text='Optional. When set, the Device device_type.manufacturer must match. Empty = any manufacturer. Objects without a manufacturer (e.g. VMs) fail closed when this is set. PROTECT prevents deleting a Manufacturer that would silently widen matching rules.',
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='zabbixtemplaterules',
                        to='dcim.manufacturer',
                    ),
                ),
                ('zabbixtemplate', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='zabbixtemplaterules', to='nbxsync.zabbixtemplate')),
                (
                    'zabbixhostgroup',
                    models.ForeignKey(
                        blank=True,
                        help_text='Optional hostgroup assigned when the rule matches. PROTECT prevents deleting a hostgroup that would silently drop this side effect from matching rules.',
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='zabbixtemplaterules',
                        to='nbxsync.zabbixhostgroup',
                    ),
                ),
                (
                    'zabbixtag',
                    models.ForeignKey(blank=True, help_text='Optional tag assigned when the rule matches. PROTECT prevents deleting a tag that would silently drop this side effect from matching rules.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='zabbixtemplaterules', to='nbxsync.zabbixtag'),
                ),
                ('tags', taggit.managers.TaggableManager(through='extras.TaggedItem', to='extras.Tag')),
            ],
            options={
                'verbose_name': 'Zabbix Template Rule',
                'verbose_name_plural': 'Zabbix Template Rules',
                'ordering': ('priority', 'name'),
            },
        ),
    ]
