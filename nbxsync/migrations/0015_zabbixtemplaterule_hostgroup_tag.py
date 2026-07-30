from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nbxsync', '0014_zabbixtemplaterule'),
    ]

    operations = [
        migrations.AddField(
            model_name='zabbixtemplaterule',
            name='zabbixhostgroup',
            field=models.ForeignKey(blank=True, help_text='Optional hostgroup assigned when the rule matches', null=True, on_delete=models.deletion.SET_NULL, related_name='zabbixtemplaterules', to='nbxsync.zabbixhostgroup'),
        ),
        migrations.AddField(
            model_name='zabbixtemplaterule',
            name='zabbixtag',
            field=models.ForeignKey(blank=True, help_text='Optional tag assigned when the rule matches', null=True, on_delete=models.deletion.SET_NULL, related_name='zabbixtemplaterules', to='nbxsync.zabbixtag'),
        ),
    ]
