document.addEventListener('DOMContentLoaded', () => {
    // Placeholder for recently viewed products logic
    const recentlyViewedContainer = document.getElementById('recentlyViewedContainer');
    const recentlyViewed = JSON.parse(localStorage.getItem('recentlyViewed')) || [];
    recentlyViewed.forEach(product => {
        const productElement = document.createElement('div');
        productElement.textContent = product;
        recentlyViewedContainer.appendChild(productElement);
    });

    document.querySelectorAll('.product-column').forEach(column => {
        column.addEventListener('mouseover', () => {
            column.style.backgroundColor = '#e0e0e0';
        });
        column.addEventListener('mouseout', () => {
            column.style.backgroundColor = '#f9f9f9';
        });
    });
});

function addToWishlist() {
    alert('Added to Wishlist');
}

function compareProduct() {
    alert('Product added for comparison');
}

function shareWishlist() {
    alert('Share your wishlist via email or social media');
}

function searchProducts() {
    const query = document.getElementById('searchInput').value;
    alert(`Search for: ${query}`);
}

function removeFromWishlist() {
    alert('Removed from Wishlist');
}