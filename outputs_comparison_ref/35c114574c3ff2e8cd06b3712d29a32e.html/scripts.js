let currentIndex = 0;
const slides = document.querySelectorAll('.carousel-slide');
const dots = document.querySelectorAll('.dot');

function showSlide(index) {
    slides.forEach((slide, i) => {
        slide.style.display = i === index ? 'block' : 'none';
        dots[i].classList.toggle('active', i === index);
    });
}

function nextSlide() {
    currentIndex = (currentIndex + 1) % slides.length;
    showSlide(currentIndex);
}

function prevSlide() {
    currentIndex = (currentIndex - 1 + slides.length) % slides.length;
    showSlide(currentIndex);
}

function currentSlide(index) {
    currentIndex = index - 1;
    showSlide(currentIndex);
}

document.addEventListener('DOMContentLoaded', () => {
    showSlide(currentIndex);
    setInterval(nextSlide, 5000); // Change slide every 5 seconds
});