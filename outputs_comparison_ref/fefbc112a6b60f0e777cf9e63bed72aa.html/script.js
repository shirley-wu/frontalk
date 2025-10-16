document.addEventListener('DOMContentLoaded', () => {
    const compareCheckboxes = document.querySelectorAll('.compare-checkbox');
    const compareNowButton = document.getElementById('compare-now');

    compareCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            const selected = document.querySelectorAll('.compare-checkbox:checked');
            compareNowButton.disabled = selected.length < 2 || selected.length > 3;
        });
    });

    compareNowButton.addEventListener('click', () => {
        const selectedProperties = Array.from(document.querySelectorAll('.compare-checkbox:checked'))
            .map(checkbox => checkbox.closest('.property-card').querySelector('h3').textContent);
        if (selectedProperties.length >= 2 && selectedProperties.length <= 3) {
            alert('Comparing: ' + selectedProperties.join(', '));
            // Navigate to compare page with selected properties
        }
    });
});