import django.db.models.deletion
import taggit.managers
from django.db import migrations, models

import utilities.json

import nbxsync.models.zabbixhostbinding


class Migration(migrations.Migration):
    """ZabbixHostBinding plus hostid PositiveBigInteger alignment on assignments."""

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('extras', '0122_charfield_null_choices'),
        ('nbxsync', '0015_zabbixtemplaterule'),
    ]

    operations = [
        migrations.CreateModel(
            name='ZabbixHostBinding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ('hostid', models.PositiveBigIntegerField()),
                ('hostname', models.CharField(blank=True, max_length=255)),
                ('assigned_object_id', models.PositiveBigIntegerField()),
                ('assigned_object_type', models.ForeignKey(limit_choices_to=nbxsync.models.zabbixhostbinding._limit_assigned_objects, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='contenttypes.contenttype')),
                ('tags', taggit.managers.TaggableManager(through='extras.TaggedItem', to='extras.Tag')),
                ('zabbixserver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='host_bindings', to='nbxsync.zabbixserver')),
            ],
            options={
                'verbose_name': 'Zabbix Host Binding',
                'verbose_name_plural': 'Zabbix Host Bindings',
                'ordering': ('-created',),
            },
            bases=(models.Model,),
        ),
        migrations.AddConstraint(
            model_name='zabbixhostbinding',
            constraint=models.UniqueConstraint(fields=('zabbixserver', 'assigned_object_type', 'assigned_object_id'), name='nbxsync_zabbixhostbinding_unique_binding_per_object', violation_error_message='A host can only be bound once to a given object on a Zabbix server.'),
        ),
        migrations.AddConstraint(
            model_name='zabbixhostbinding',
            constraint=models.UniqueConstraint(fields=('zabbixserver', 'hostid'), name='nbxsync_zabbixhostbinding_unique_hostid_per_server', violation_error_message='The same Zabbix host ID cannot be bound to multiple objects on a server.'),
        ),
        # Align assignment hostid storage with ZabbixHostBinding.hostid (PositiveBigInteger).
        migrations.AlterField(
            model_name='zabbixserverassignment',
            name='hostid',
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
    ]
