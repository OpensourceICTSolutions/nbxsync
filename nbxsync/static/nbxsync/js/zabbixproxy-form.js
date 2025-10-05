document.addEventListener('DOMContentLoaded', function () {
    const operatingmodeField = document.getElementById('id_operating_mode');
    const customTimeoutField = document.getElementById('id_custom_timeouts');
    const tlsacceptField = document.getElementById('id_tls_accept');
    const tlsconnectField = document.getElementById('id_tls_connect');
    const tlspskField = document.getElementById('id_tls_psk');
    const TogglePSKButton = document.getElementById('toggle-psk');

    const pskWrapper = document.getElementById('tlspsk-wrapper');
    const certWrapper = document.getElementById('tlscert-wrapper');
    const customTimeoutWrapper = document.getElementById('customtimeout-wrapper');
    const opmodeActive = document.querySelector('#opmode-active-wrapper');
    const opmodePassive = document.querySelector('#opmode-passive-wrapper');

    const tlsconnectFieldWrapper = tlsconnectField?.closest('.col');
    const tlsconnectLabelWrapper = document.querySelector('label[for="id_tls_connect-ts-control"]')?.closest('.col-sm-3');

    const tlsacceptFieldWrapper = tlsacceptField?.closest('.col');
    const tlsacceptLabelWrapper = document.querySelector('label[for="id_tls_accept-ts-control"]')?.closest('.col-sm-3');

    // --- Helpers ---
    function toggleDisplay(el, show) {
        if (el) el.style.display = show ? '' : 'none';
    }

    function getSelectedValues(selectElement) {
        // Handles native select and TomSelect
        if (selectElement?.tomselect) {
            return Array.isArray(selectElement.tomselect.getValue())
                ? selectElement.tomselect.getValue()
                : [selectElement.tomselect.getValue()];
        }
        return Array.from(selectElement?.selectedOptions || []).map(opt => opt.value);
    }

    function getSingleValue(selectElement) {
        if (selectElement?.tomselect) {
            return selectElement.tomselect.getValue();
        }
        return selectElement?.value;
    }

    // --- Logic ---
    function toggleTLSAcceptFields() {
        const selectedValues = getSelectedValues(tlsacceptField);
        const showPSK = selectedValues.includes("2");
        const showCert = selectedValues.includes("4");
        const operatingMode = operatingmodeField.value;

        if (operatingMode === '0') { // Active Proxy
            toggleDisplay(pskWrapper, showPSK);
            toggleDisplay(certWrapper, showCert);
        }

    }

    function toggleTLSConnectFields() {
        const selectedValue = getSingleValue(tlsconnectField);
        const showPSK = selectedValue === "2";
        const showCert = selectedValue === "4";
        const operatingMode = operatingmodeField.value;

        if (operatingMode === '1') { // Passive Proxy
            toggleDisplay(pskWrapper, showPSK);
            toggleDisplay(certWrapper, showCert);
        }
    }

    function toggleCustomTimeoutFields() {
        if (!customTimeoutField || !customTimeoutWrapper) return;
        toggleDisplay(customTimeoutWrapper, customTimeoutField.checked);
    }

    function toggleOperatingModeFields() {
        if (!operatingmodeField) return;

        const operatingMode = operatingmodeField.value;

        if (operatingMode === '0') { // Active Proxy
            toggleDisplay(opmodeActive, true);
            toggleDisplay(opmodePassive, false);

            toggleDisplay(tlsconnectFieldWrapper, false);
            toggleDisplay(tlsconnectLabelWrapper, false);

            toggleDisplay(tlsacceptFieldWrapper, true);
            toggleDisplay(tlsacceptLabelWrapper, true);
        } else if (operatingMode === '1') { // Passive Proxy
            toggleDisplay(opmodeActive, false);
            toggleDisplay(opmodePassive, true);

            toggleDisplay(tlsconnectFieldWrapper, true);
            toggleDisplay(tlsconnectLabelWrapper, true);

            toggleDisplay(tlsacceptFieldWrapper, false);
            toggleDisplay(tlsacceptLabelWrapper, false);
        }
    }

    function togglePSKVisibility() {
        tlspskField.type = tlspskField.type === "password" ? "text" : "password";
    }

    // --- Initial evaluation (defer to ensure widgets are ready) ---
    requestAnimationFrame(() => {
        toggleOperatingModeFields();
        toggleTLSAcceptFields();
        toggleTLSConnectFields();
        toggleCustomTimeoutFields();
    });

    // --- Event listeners ---
    operatingmodeField?.addEventListener('change', () => {
        toggleOperatingModeFields();
        toggleTLSAcceptFields();
        toggleTLSConnectFields();
    });

    tlsacceptField?.addEventListener('change', toggleTLSAcceptFields);
    tlsconnectField?.addEventListener('change', toggleTLSConnectFields);
    customTimeoutField?.addEventListener('change', toggleCustomTimeoutFields);
    TogglePSKButton?.addEventListener('click', togglePSKVisibility);
});


