// Carousel functionality
let currentSlide = 0;
const slides = document.querySelectorAll('.slide');
const dots = document.querySelectorAll('.dot');

function showSlide(index) {
    slides.forEach((slide, i) => {
        slide.style.display = i === index ? 'block' : 'none';
    });
    dots.forEach((dot, i) => {
        dot.classList.toggle('active', i === index);
    });
}

document.querySelectorAll('.dot').forEach((dot, index) => {
    dot.addEventListener('click', () => {
        currentSlide = index;
        showSlide(currentSlide);
    });
});

showSlide(currentSlide);

// Dynamic background for featured episode
document.querySelector('.dynamic-background').style.backgroundColor = '#f0f8ff';

// Event listener for search icon
document.getElementById('search-icon').addEventListener('click', () => {
    window.location.href = 'search.html';
});

// Placeholder for search functionality
console.log('Search functionality placeholder');