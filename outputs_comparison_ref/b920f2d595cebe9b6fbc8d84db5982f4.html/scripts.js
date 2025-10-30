document.addEventListener('DOMContentLoaded', () => {
    const advancedSearchLink = document.querySelector('.advanced-search-link');
    const advancedSearchSection = document.getElementById('advanced-search');

    advancedSearchLink.addEventListener('click', (event) => {
        event.preventDefault();
        advancedSearchSection.style.display = advancedSearchSection.style.display === 'none' ? 'block' : 'none';
    });
});