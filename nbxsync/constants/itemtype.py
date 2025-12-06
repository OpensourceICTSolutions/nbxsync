from nbxsync.choices import HostInterfaceRequirementChoices

ITEM_TYPE_TO_INTERFACE_REQUIREMENT = {
    0: [HostInterfaceRequirementChoices.AGENT],  # Zabbix agent
    2: [HostInterfaceRequirementChoices.NONE],  # Zabbix trapper
    3: [HostInterfaceRequirementChoices.ANY],  # Simple check
    5: [HostInterfaceRequirementChoices.NONE],  # Internal
    7: [HostInterfaceRequirementChoices.NONE],  # Agent (active)
    9: [HostInterfaceRequirementChoices.ANY],  # Web item
    10: [HostInterfaceRequirementChoices.ANY],  # External check
    11: [HostInterfaceRequirementChoices.ANY],  # DB monitor
    12: [HostInterfaceRequirementChoices.IPMI],  # IPMI agent
    13: [HostInterfaceRequirementChoices.ANY],  # SSH agent
    14: [HostInterfaceRequirementChoices.ANY],  # TELNET
    15: [HostInterfaceRequirementChoices.NONE],  # Calculated
    16: [HostInterfaceRequirementChoices.JMX],  # JMX
    17: [HostInterfaceRequirementChoices.SNMP],  # SNMP trap
    18: [HostInterfaceRequirementChoices.NONE],  # Dependent
    19: [HostInterfaceRequirementChoices.NONE],  # HTTP agent // should be none
    20: [HostInterfaceRequirementChoices.SNMP],  # SNMP agent
    21: [HostInterfaceRequirementChoices.SNMP],  # Script
    22: [HostInterfaceRequirementChoices.NONE],  # Browser
}
