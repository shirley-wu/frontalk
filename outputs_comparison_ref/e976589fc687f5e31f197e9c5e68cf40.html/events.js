document.addEventListener('DOMContentLoaded', function() {
    const filter = document.getElementById('event-filter');
    const events = document.querySelectorAll('.event');

    filter.addEventListener('change', function() {
        const selectedCategory = filter.value;
        events.forEach(event => {
            if (selectedCategory === 'all' || event.dataset.category === selectedCategory) {
                event.style.display = 'block';
            } else {
                event.style.display = 'none';
            }
        });
    });
});