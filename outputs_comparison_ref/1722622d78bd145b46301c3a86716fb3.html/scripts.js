document.addEventListener("DOMContentLoaded", () => {
    const subscribeButton = document.getElementById('subscribeButton');
    const carouselSlides = document.querySelectorAll('.carousel-slide');
    let currentSlide = 0;

    function showSlide(index) {
        carouselSlides.forEach((slide, i) => {
            slide.style.display = i === index ? 'block' : 'none';
        });
    }

    function nextSlide() {
        currentSlide = (currentSlide + 1) % carouselSlides.length;
        showSlide(currentSlide);
    }

    function prevSlide() {
        currentSlide = (currentSlide - 1 + carouselSlides.length) % carouselSlides.length;
        showSlide(currentSlide);
    }

    document.querySelector('.carousel-next').addEventListener('click', nextSlide);
    document.querySelector('.carousel-prev').addEventListener('click', prevSlide);

    showSlide(currentSlide);

    subscribeButton.addEventListener('mouseenter', () => {
        subscribeButton.style.transform = 'scale(1.1)';
    });

    subscribeButton.addEventListener('mouseleave', () => {
        subscribeButton.style.transform = 'scale(1)';
    });

    const filterOptions = document.getElementById('filterOptions');
    filterOptions.addEventListener('change', (event) => {
        const genre = event.target.value;
        const authors = document.querySelectorAll('.author-profile');

        authors.forEach(author => {
            const badge = author.querySelector('.badge');
            if (genre === 'all' || badge.getAttribute('data-genre') === genre) {
                author.style.display = 'block';
            } else {
                author.style.display = 'none';
            }
        });
    });
});