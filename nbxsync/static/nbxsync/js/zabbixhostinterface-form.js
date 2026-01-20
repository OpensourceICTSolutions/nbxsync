document.addEventListener('DOMContentLoaded', () => {
  const getEl = id => document.getElementById(id);
  const toggleDisplay = (el, show) => { if (el) el.style.display = show ? '' : 'none'; };

  // --- Fields ---
  const typeField = getEl('id_type');
  const useIpField = getEl('id_useip');
  const snmpVersionField = getEl('id_snmp_version');
  const snmpv3securitylevelField = getEl('id_snmpv3_security_level');
  const snmpv3AuthPassField = getEl('id_snmpv3_authentication_passphrase');
  const snmpv3PrivPassField = getEl('id_snmpv3_privacy_passphrase');
  const tlsacceptField = getEl('id_tls_accept');
  const tlsconnectField = getEl('id_tls_connect');
  const tlspskField = getEl('id_tls_psk');
  const ipmipasswordField = getEl('id_ipmi_password');
  const portField = getEl('id_port');
  const useDefaultPortCheckbox = getEl('id_use_defaultport');

  // --- Wrappers ---
  const ipWrapper = getEl('ip-address-wrapper');
  const dnsWrapper = getEl('dns-wrapper');
  const ipmiWrapper = getEl('ipmi-wrapper');
  const snmpWrapper = getEl('snmp-version-wrapper');
  const snmpv2Wrapper = getEl('snmpv2-wrapper');
  const snmpv3Wrapper = getEl('snmpv3-wrapper');
  const snmpv3authWrapper = getEl('snmpv3-auth-wrapper');
  const snmpv3privWrapper = getEl('snmpv3-priv-wrapper');
  const agentWrapper = getEl('agent-wrapper');
  const pskWrapper = getEl('tlspsk-wrapper');
  const certWrapper = getEl('tlscert-wrapper');

  // --- Buttons ---
  const togglePSKButton = getEl('toggle-psk');
  const toggleSNMPv3PrivButton = getEl('toggle-snmpv3-priv-pass');
  const toggleSNMPv3AuthButton = getEl('toggle-snmpv3-auth-pass');
  const toggleIPMIPasswordButton = getEl('toggle-ipmipassword');

  // --- Helpers ---
  const defaultPorts = {
    '1': 10050,   // Agent
    '2': 161,     // SNMP
    '3': 623,     // JMX
    '4': 12345    // IPMI
  };

  const getSelectedValues = el =>
    el?.tomselect ? [].concat(el.tomselect.getValue()) :
    Array.from(el?.selectedOptions || []).map(opt => opt.value);

  const getSingleValue = el =>
    el?.tomselect ? el.tomselect.getValue() : el?.value;

  const getDefaultPort = typeVal => defaultPorts[typeVal] ?? null;
  const valuesEqual = (a, b) => String(a).trim() === String(b).trim();

  // --- Address toggle ---
  const toggleAddressFields = () => {
    ipWrapper?.classList.toggle('d-none', useIpField.value !== '1');
    dnsWrapper?.classList.toggle('d-none', useIpField.value !== '0');
  };

  // --- IPMI toggle ---
  const toggleIPMIVisibility = () => toggleDisplay(ipmiWrapper, typeField.value === '3');

  // --- SNMP toggle ---
  const toggleSNMPVersionVisibility = () => {
    const isSNMP = typeField.value === '2';
    const isSNMPv2 = ['1','2'].includes(snmpVersionField.value);
    const isSNMPv3 = snmpVersionField.value === '3';

    toggleDisplay(snmpWrapper, isSNMP);
    toggleDisplay(snmpv2Wrapper, isSNMP && isSNMPv2);
    toggleDisplay(snmpv3Wrapper, isSNMP && isSNMPv3);

    if (isSNMP && isSNMPv3) toggleSNMPV3SecurityLevelFields();
  };

  const toggleSNMPV3SecurityLevelFields = () => {
    const lvl = snmpv3securitylevelField.value;
    toggleDisplay(snmpv3authWrapper, lvl === '1' || lvl === '2');
    toggleDisplay(snmpv3privWrapper, lvl === '2');
  };

  // --- TLS toggle ---
  const updateTLSFieldVisibility = () => {
    const isAgent = typeField.value === '1';
    if (!isAgent) return toggleDisplay(agentWrapper, false);

    const acceptValues = getSelectedValues(tlsacceptField);
    const connectValue = getSingleValue(tlsconnectField);

    toggleDisplay(agentWrapper, true);
    toggleDisplay(pskWrapper, acceptValues.includes("2") || connectValue === "2");
    toggleDisplay(certWrapper, acceptValues.includes("4") || connectValue === "4");
  };

  // --- Show/hide secrets ---
  const togglePSKVisibility = () => {
    tlspskField.type = tlspskField.type === "password" ? "text" : "password";
  };
  const toggleIPMIPasswordVisibility = () => {
    ipmipasswordField.type = ipmipasswordField.type === "password" ? "text" : "password";
  };

  const toggleSNMPv3PrivVisibility = () => {
    snmpv3PrivPassField.type = snmpv3PrivPassField.type === "password" ? "text" : "password";
  };
  const toggleSNMPv3AuthVisibility = () => {
    snmpv3AuthPassField.type = snmpv3AuthPassField.type === "password" ? "text" : "password";
  };

  // --- Port logic ---
  const applyDefaultPortAndReadOnly = () => {
    const defaultPortValue = getDefaultPort(typeField.value);
    if (defaultPortValue == null) {
      useDefaultPortCheckbox.checked = false;
      portField.readOnly = false;
      return;
    }
    portField.value = defaultPortValue;
    portField.readOnly = true;
    useDefaultPortCheckbox.checked = true;
  };

  const unlockPortFieldForCustom = () => { portField.readOnly = false; };

  const onUseDefaultPortCheckboxChange = () => {
    const defaultPortValue = getDefaultPort(typeField.value);
    if (defaultPortValue == null) return unlockPortFieldForCustom();
    if (useDefaultPortCheckbox.checked) applyDefaultPortAndReadOnly();
    else unlockPortFieldForCustom();
  };

  const onPortInput = () => {
    const defaultPortValue = getDefaultPort(typeField.value);
    if (defaultPortValue != null && !useDefaultPortCheckbox.checked && valuesEqual(portField.value, defaultPortValue)) {
      applyDefaultPortAndReadOnly();
    }
  };

  const onTypeChangePort = () => {
    const defaultPortValue = getDefaultPort(typeField.value);
    if (defaultPortValue == null) {
      useDefaultPortCheckbox.checked = false;
      portField.readOnly = false;
      return;
    }
    if (useDefaultPortCheckbox.checked) {
      applyDefaultPortAndReadOnly();
    } else {
      portField.readOnly = false;
      if (!portField.value) applyDefaultPortAndReadOnly();
    }
  };

  // --- Init (slight defer for TomSelect) ---
  setTimeout(() => {
    toggleAddressFields();
    toggleSNMPVersionVisibility();
    toggleSNMPV3SecurityLevelFields();
    toggleIPMIVisibility();
    updateTLSFieldVisibility();
    if (!portField.value) applyDefaultPortAndReadOnly();
  }, 0);

  // --- Event listeners ---
  useIpField?.addEventListener('change', toggleAddressFields);
  typeField?.addEventListener('change', () => {
    toggleSNMPVersionVisibility();
    toggleIPMIVisibility();
    updateTLSFieldVisibility();
    onTypeChangePort();
  });
  snmpVersionField?.addEventListener('change', toggleSNMPVersionVisibility);
  snmpv3securitylevelField?.addEventListener('change', toggleSNMPV3SecurityLevelFields);
  tlsacceptField?.addEventListener('change', updateTLSFieldVisibility);
  tlsconnectField?.addEventListener('change', updateTLSFieldVisibility);
  togglePSKButton?.addEventListener('click', togglePSKVisibility);

  toggleSNMPv3AuthButton?.addEventListener('click', toggleSNMPv3AuthVisibility);
  toggleSNMPv3PrivButton?.addEventListener('click', toggleSNMPv3PrivVisibility);

  toggleIPMIPasswordButton?.addEventListener('click', toggleIPMIPasswordVisibility);
  useDefaultPortCheckbox?.addEventListener('change', onUseDefaultPortCheckboxChange);
  portField?.addEventListener('input', onPortInput);
});
