document.addEventListener('DOMContentLoaded', function() {
    // Carousel functionality
    let currentSlide = 0;
    const slides = document.querySelectorAll('.carousel-slide');
    const totalSlides = slides.length;
    
    document.querySelector('.carousel-nav.next').addEventListener('click', function() {
        slides[currentSlide].style.display = 'none';
        currentSlide = (currentSlide + 1) % totalSlides;
        slides[currentSlide].style.display = 'block';
    });

    document.querySelector('.carousel-nav.prev').addEventListener('click', function() {
        slides[currentSlide].style.display = 'none';
        currentSlide = (currentSlide - 1 + totalSlides) % totalSlides;
        slides[currentSlide].style.display = 'block';
    });

    // Sorting functionality for reviews
    document.getElementById('sort-reviews').addEventListener('change', function() {
        // Implement sorting logic here
        alert('Sorting reviews by ' + this.value);
    });
});

function expandDish(dishElement) {
    alert('Expanding dish details');
    // Implement expand logic here
}