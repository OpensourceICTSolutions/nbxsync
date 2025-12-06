from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem

items = (
    PluginMenuItem(
        link='plugins:nbxsync:zabbixserver_list',
        link_text='Servers',
        permissions=['nbxsync.view_zabbixserver'],
        buttons=(
            PluginMenuButton(
                link='plugins:nbxsync:zabbixserver_add',
                title='Add',
                icon_class='mdi mdi-plus-thick',
            ),
        ),
    ),
    PluginMenuItem(
        link='plugins:nbxsync:zabbixproxy_list',
        link_text='Proxies',
        permissions=['nbxsync.view_zabbixproy'],
        buttons=(
            PluginMenuButton(
                link='plugins:nbxsync:zabbixproxy_add',
                title='Add',
                icon_class='mdi mdi-plus-thick',
            ),
        ),
    ),
    PluginMenuItem(
        link='plugins:nbxsync:zabbixproxygroup_list',
        link_text='Proxy Groups',
        permissions=['nbxsync.view_zabbixproxygroup'],
        buttons=(
            PluginMenuButton(
                link='plugins:nbxsync:zabbixproxygroup_add',
                title='Add',
                icon_class='mdi mdi-plus-thick',
            ),
        ),
    ),
    PluginMenuItem(
        link='plugins:nbxsync:zabbixtemplate_list',
        link_text='Templates',
        permissions=['nbxsync.view_zabbixtemplate'],
        buttons=(
            PluginMenuButton(
                link='plugins:nbxsync:zabbixtemplate_add',
                title='Add',
                icon_class='mdi mdi-plus-thick',
            ),
        ),
    ),
    PluginMenuItem(
        link='plugins:nbxsync:zabbixmacro_list',
        link_text='Macros',
        permissions=['nbxsync.view_zabbixmacro'],
        buttons=(
            PluginMenuButton(
                link='plugins:nbxsync:zabbixmacro_add',
                title='Add',
                icon_class='mdi mdi-plus-thick',
            ),
        ),
    ),
    PluginMenuItem(
        link='plugins:nbxsync:zabbixtag_list',
        link_text='Tags',
        permissions=['nbxsync.view_zabbixtag'],
        buttons=(
            PluginMenuButton(
                link='plugins:nbxsync:zabbixtag_add',
                title='Add',
                icon_class='mdi mdi-plus-thick',
            ),
        ),
    ),
    PluginMenuItem(
        link='plugins:nbxsync:zabbixhostgroup_list',
        link_text='Hostgroups',
        permissions=['nbxsync.view_zabbixhostgroup'],
        buttons=(
            PluginMenuButton(
                link='plugins:nbxsync:zabbixhostgroup_add',
                title='Add',
                icon_class='mdi mdi-plus-thick',
            ),
        ),
    ),
    PluginMenuItem(
        link='plugins:nbxsync:zabbixconfigurationgroup_list',
        link_text='Configuration groups',
        permissions=['nbxsync.view_zabbixconfigurationgroup'],
        buttons=(
            PluginMenuButton(
                link='plugins:nbxsync:zabbixconfigurationgroup_add',
                title='Add',
                icon_class='mdi mdi-plus-thick',
            ),
        ),
    ),
    PluginMenuItem(
        link='plugins:nbxsync:zabbixmaintenance_list',
        link_text='Maintenance',
        permissions=['nbxsync.view_zabbixmaintenance'],
        buttons=(
            PluginMenuButton(
                link='plugins:nbxsync:zabbixmaintenance_add',
                title='Add',
                icon_class='mdi mdi-plus-thick',
            ),
        ),
    ),
)
menu = PluginMenu(label='Zabbix', groups=(('zabbix', items),), icon_class='mdi mdi-monitor-multiple')
