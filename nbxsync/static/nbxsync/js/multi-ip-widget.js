document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('allowedip-container');
    const addButton = document.getElementById('add-allowedip');
    const fieldName = addButton.dataset.fieldName;

    addButton.addEventListener('click', function () {
        // Create new row
        const row = document.createElement('div');
        row.classList.add('row', 'mb-3');
        row.innerHTML = `
            <div class="col">
                <div class="d-flex">
                    <input type="text" name="${fieldName}" class="form-control" placeholder="IP Address">
                    <button type="button" title="Remove" class="btn btn-outline-danger ms-1 remove-allowedip">
                        <i class="mdi mdi-minus-circle"></i>
                    </button>
                </div>
            </div>
        `;
        container.appendChild(row);
    });

    container.addEventListener('click', function (e) {
        const removeBtn = e.target.closest('.remove-allowedip');
        if (removeBtn) {
            const row = removeBtn.closest('.row.mb-3');
            if (row && row.querySelector(`input[name="${fieldName}"]`)) {
                row.remove();
            }
        }
    });
});
