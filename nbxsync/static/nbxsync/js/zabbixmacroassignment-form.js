document.addEventListener('DOMContentLoaded', () => {
    const valueField = document.getElementById('id_value');
    const toggleBtn = document.getElementById('toggle-psk');
    const icon = document.getElementById('toggle-icon');

    // If the field or button isn't present, do nothing
    if (!valueField || !toggleBtn) return;

    // Convert field to password type on page load
    valueField.type = 'password';

    toggleBtn.addEventListener('click', () => {
        // Toggle input type
        const isPassword = valueField.type === 'password';
        valueField.type = isPassword ? 'text' : 'password';

        // Swap the icon (Material Design Icons)
        if (isPassword) {
            icon.classList.remove('mdi-eye');
            icon.classList.add('mdi-eye-off');
        } else {
            icon.classList.remove('mdi-eye-off');
            icon.classList.add('mdi-eye');
        }
    });
});
