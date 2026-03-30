document.addEventListener('DOMContentLoaded', () => {
    // Implement search functionality
    const searchBtn = document.getElementById('search-btn');
    const searchInput = document.getElementById('search');

    searchBtn.addEventListener('click', () => {
        const query = searchInput.value.toLowerCase();
        const posts = document.querySelectorAll('#latest-posts article');
        
        posts.forEach(post => {
            const title = post.querySelector('h3').textContent.toLowerCase();
            const summary = post.querySelector('p').textContent.toLowerCase();
            if (title.includes(query) || summary.includes(query)) {
                post.style.display = 'block';
            } else {
                post.style.display = 'none';
            }
        });
    });

    // Implement category filter
    const categoryFilter = document.getElementById('categories');
    categoryFilter.addEventListener('change', () => {
        const selectedCategory = categoryFilter.value;
        const posts = document.querySelectorAll('#latest-posts article');
        
        posts.forEach(post => {
            if (selectedCategory === 'all' || post.classList.contains(selectedCategory)) {
                post.style.display = 'block';
            } else {
                post.style.display = 'none';
            }
        });
    });

    // Implement carousel functionality for featured articles
    const carousel = document.querySelector('.carousel');
    carousel.addEventListener('wheel', (evt) => {
        evt.preventDefault();
        carousel.scrollBy({
            left: evt.deltaY < 0 ? -300 : 300,
            behavior: 'smooth'
        });
    });

    // Implement carousel functionality for user testimonials
    const testimonialCarousel = document.querySelector('.testimonial-carousel');
    testimonialCarousel.addEventListener('wheel', (evt) => {
        evt.preventDefault();
        testimonialCarousel.scrollBy({
            left: evt.deltaY < 0 ? -300 : 300,
            behavior: 'smooth'
        });
    });

    // Implement accordion functionality for quick tips
    const tips = document.querySelectorAll('.accordion .tip');
    tips.forEach(tip => {
        tip.addEventListener('click', () => {
            tip.classList.toggle('active');
            const description = tip.querySelector('p');
            if (tip.classList.contains('active')) {
                description.style.maxHeight = description.scrollHeight + 'px';
            } else {
                description.style.maxHeight = '0';
            }
        });
    });
});