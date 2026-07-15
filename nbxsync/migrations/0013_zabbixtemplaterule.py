import taggit.managers
from django.db import migrations, models

import utilities.json


class Migration(migrations.Migration):
    dependencies = [
        ('extras', '0134_owner'),
        ('nbxsync', '0012_zabbixserver_skip_version_check'),
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
                ('enabled', models.BooleanField(default=True)),
                ('priority', models.IntegerField(default=100)),
                ('zabbixtemplate', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='zabbixtemplaterules', to='nbxsync.zabbixtemplate')),
                ('tags', taggit.managers.TaggableManager(through='extras.TaggedItem', to='extras.Tag')),
            ],
            options={
                'verbose_name': 'Zabbix Template Rule',
                'verbose_name_plural': 'Zabbix Template Rules',
                'ordering': ('priority', 'name'),
            },
        ),
    ]
