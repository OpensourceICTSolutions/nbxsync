document.addEventListener('DOMContentLoaded', function () {
    const tokenField = document.getElementById('id_token');
    const ToggleTokenButton = document.getElementById('toggle-token');

    // --- Logic ---
    function toggleTokenVisibility() {
        tokenField.type = tokenField.type === "password" ? "text" : "password";
    }

    ToggleTokenButton?.addEventListener('click', toggleTokenVisibility);
});


