document.getElementById("supportButton").addEventListener("click", function() {
    alert("Live chat support coming soon!");
});

document.getElementById("gameSearchForm").addEventListener("submit", function(event) {
    event.preventDefault();
    alert("Search functionality is under development!");
});

// Carousel functionality
let currentImageIndex = 0;
const images = document.querySelectorAll('.carousel-images img');
const dots = document.querySelectorAll('.carousel-dots .dot');

function updateCarousel() {
    images.forEach((img, index) => {
        img.style.transform = `translateX(-${currentImageIndex * 100}%)`;
        dots[index].classList.toggle('active', index === currentImageIndex);
    });
}

document.querySelector('.carousel-controls .prev').addEventListener('click', () => {
    currentImageIndex = (currentImageIndex > 0) ? currentImageIndex - 1 : images.length - 1;
    updateCarousel();
});

document.querySelector('.carousel-controls .next').addEventListener('click', () => {
    currentImageIndex = (currentImageIndex < images.length - 1) ? currentImageIndex + 1 : 0;
    updateCarousel();
});

dots.forEach((dot, index) => {
    dot.addEventListener('click', () => {
        currentImageIndex = index;
        updateCarousel();
    });
});

updateCarousel();