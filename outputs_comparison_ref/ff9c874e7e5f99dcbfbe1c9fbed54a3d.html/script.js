let currentIndex = 0;
const items = document.querySelectorAll('.carousel-item');

function showItem(index) {
    items.forEach((item, i) => {
        item.style.display = i === index ? 'block' : 'none';
    });
}

document.getElementById('next').addEventListener('click', () => {
    currentIndex = (currentIndex + 1) % items.length;
    showItem(currentIndex);
});

document.getElementById('prev').addEventListener('click', () => {
    currentIndex = (currentIndex - 1 + items.length) % items.length;
    showItem(currentIndex);
});

// Initialize carousel
showItem(currentIndex);