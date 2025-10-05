import datetime

from django.utils.timezone import make_aware

from nbxsync.models import ZabbixTemplate
from nbxsync.choices import HostInterfaceRequirementChoices
from nbxsync.constants import ITEM_TYPE_TO_INTERFACE_REQUIREMENT
from nbxsync.utils import ZabbixConnection
from nbxsync.utils.helpers import create_or_update_zabbixmacro, create_or_update_zabbixtemplate

__all__ = ('SyncTemplatesJob',)


class SyncTemplatesJob:
    def __init__(self, **kwargs):
        self.instance = kwargs.get('instance')

    def run(self):
        try:
            with ZabbixConnection(self.instance) as api:
                templates = api.template.get(output='extend', selectMacros='extend')

                for template in templates:
                    zabbixtemplate = create_or_update_zabbixtemplate(template=template, zabbixserver=self.instance)
                    interface_requirements = set()

                    if not zabbixtemplate:
                        # print(f"Template {template['name']} wasn't found!")
                        # No template found and not created, something went wrong...
                        continue

                    for macro in template['macros']:
                        create_or_update_zabbixmacro(macro=macro, zabbixtemplate=zabbixtemplate)

                    # Get all items on the template
                    items_on_template = api.item.get(output='extend', templateids=template['templateid'], inherited=False)
                    # Get all discovery rules on the template
                    discovery_rules_on_template = api.discoveryrule.get(
                        templateids=[template['templateid']],
                        selectFilter='extend',
                        selectGraphs='extend',
                        selectHostPrototypes='extend',
                        selectItems='extend',
                    )

                    # loop through the items
                    for discovery_rule in discovery_rules_on_template:
                        for item in discovery_rule['items']:
                            item_type = int(item.get('type', -1))
                            requirements = ITEM_TYPE_TO_INTERFACE_REQUIREMENT.get(item_type, [HostInterfaceRequirementChoices.NONE])
                            interface_requirements.update(requirements)

                    for item in items_on_template:
                        item_type = int(item.get('type', -1))
                        requirements = ITEM_TYPE_TO_INTERFACE_REQUIREMENT.get(item_type, [HostInterfaceRequirementChoices.NONE])
                        interface_requirements.update(requirements)

                    # Normalize the interface requirements
                    if HostInterfaceRequirementChoices.ANY in interface_requirements:
                        final_requirements = [HostInterfaceRequirementChoices.ANY]
                    elif HostInterfaceRequirementChoices.NONE in interface_requirements and len(interface_requirements) == 1:
                        final_requirements = [HostInterfaceRequirementChoices.NONE]
                    else:
                        final_requirements = [r for r in interface_requirements if r != HostInterfaceRequirementChoices.NONE]

                    # Update the template object if needed
                    if set(zabbixtemplate.interface_requirements) != set(final_requirements):
                        zabbixtemplate.interface_requirements = list(interface_requirements)
                        zabbixtemplate.save()

                # Next logic: Cleanup all templates from Netbox that aren't present in Zabbix anymore
                # Get all template IDs in Netbox
                netbox_template_ids = set(ZabbixTemplate.objects.filter(zabbixserver_id=self.instance.id).values_list('templateid', flat=True))

                # Get all IDs from the templates as retrieved from Zabbix
                zabbix_template_ids = {int(t['templateid']) for t in templates}

                # What to delete = present in Netbox but not in Zabbix
                to_delete_ids = netbox_template_ids - zabbix_template_ids

                if to_delete_ids:
                    # Delete all 'orphan' templates from Netbox so its in sync again
                    ZabbixTemplate.objects.filter(zabbixserver_id=self.instance.id, templateid__in=to_delete_ids).delete()

            self.instance.last_sync_state = True
            self.instance.last_sync = make_aware(datetime.datetime.now())
            self.instance.last_sync_message = 'Succes'
            self.instance.save()

        except ConnectionError as e:
            self.instance.last_sync_state = False
            self.instance.last_sync = make_aware(datetime.datetime.now())
            self.instance.last_sync_message = f'Login error: {e}'
            self.instance.save()
            raise ConnectionError(f'Login error: {e}')
        except Exception as e:
            self.instance.last_sync_state = False
            self.instance.last_sync = make_aware(datetime.datetime.now())
            self.instance.last_sync_message = f'Unexpected error: {e}'
            self.instance.save()
            raise RuntimeError(f'Unexpected error: {e}')
