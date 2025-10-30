function filterListings(category) {
    const listings = document.querySelectorAll('#listings .listing');
    listings.forEach(listing => {
        if (category === 'all' || listing.dataset.category === category) {
            listing.style.display = 'block';
        } else {
            listing.style.display = 'none';
        }
    });
}

function toggleFavorite(button) {
    const listing = button.parentElement;
    const favoritesList = document.getElementById('favorites-list');
    if (button.textContent === '♡') {
        button.textContent = '♥';
        const clone = listing.cloneNode(true);
        clone.querySelector('button').onclick = () => toggleFavorite(clone.querySelector('button'));
        favoritesList.appendChild(clone);
    } else {
        button.textContent = '♡';
        favoritesList.removeChild(listing);
    }
}

function toggleCalendarView() {
    const calendar = document.getElementById('calendar');
    // Logic to toggle between monthly and weekly view
}