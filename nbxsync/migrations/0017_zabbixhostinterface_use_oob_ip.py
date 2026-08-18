from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nbxsync', '0016_zabbixhostbinding'),
    ]

    operations = [
        migrations.AddField(
            model_name='zabbixhostinterface',
            name='use_oob_ip',
            field=models.BooleanField(
                default=False,
                verbose_name='Use OOB IP',
                help_text='When enabled and no static IP is set, resolve the interface IP '
                'from the device oob_ip field. If the device has no oob_ip, sync '
                'skips this interface and keeps any existing Zabbix interface '
                'unless inherited deletion is enabled.',
            ),
        ),
    ]
