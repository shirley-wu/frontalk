let currentFeaturedIndex = 0;
let currentFactIndex = 0;

function nextFeatured() {
    const items = document.querySelectorAll('#featured-birds .carousel-item');
    items[currentFeaturedIndex].style.transform = 'translateX(-100%)';
    currentFeaturedIndex = (currentFeaturedIndex + 1) % items.length;
    items[currentFeaturedIndex].style.transform = 'translateX(0)';
}

function prevFeatured() {
    const items = document.querySelectorAll('#featured-birds .carousel-item');
    items[currentFeaturedIndex].style.transform = 'translateX(100%)';
    currentFeaturedIndex = (currentFeaturedIndex - 1 + items.length) % items.length;
    items[currentFeaturedIndex].style.transform = 'translateX(0)';
}

function nextFact() {
    const items = document.querySelectorAll('#bird-facts .carousel-item');
    items[currentFactIndex].style.transform = 'translateX(-100%)';
    currentFactIndex = (currentFactIndex + 1) % items.length;
    items[currentFactIndex].style.transform = 'translateX(0)';
}

function prevFact() {
    const items = document.querySelectorAll('#bird-facts .carousel-item');
    items[currentFactIndex].style.transform = 'translateX(100%)';
    currentFactIndex = (currentFactIndex - 1 + items.length) % items.length;
    items[currentFactIndex].style.transform = 'translateX(0)';
}

function showAdvancedFilters() {
    document.getElementById('advanced-filters').style.display = 'block';
}