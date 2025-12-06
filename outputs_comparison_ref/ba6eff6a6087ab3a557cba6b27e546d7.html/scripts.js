document.addEventListener('DOMContentLoaded', () => {
    const slides = document.querySelectorAll('.carousel-slide');
    const dots = document.querySelectorAll('.carousel-dots .dot');
    let currentSlide = 0;

    function showSlide(index) {
        slides.forEach((slide, i) => {
            slide.style.display = i === index ? 'block' : 'none';
            dots[i].classList.toggle('active', i === index);
        });
    }

    function nextSlide() {
        currentSlide = (currentSlide + 1) % slides.length;
        showSlide(currentSlide);
    }

    function prevSlide() {
        currentSlide = (currentSlide - 1 + slides.length) % slides.length;
        showSlide(currentSlide);
    }

    document.querySelector('.carousel-next').addEventListener('click', nextSlide);
    document.querySelector('.carousel-prev').addEventListener('click', prevSlide);
    dots.forEach((dot, index) => dot.addEventListener('click', () => showSlide(index)));

    showSlide(currentSlide);

    setInterval(nextSlide, 5000);

    window.addToWishlist = function() {
        alert('Artwork added to wishlist!');
    };
});