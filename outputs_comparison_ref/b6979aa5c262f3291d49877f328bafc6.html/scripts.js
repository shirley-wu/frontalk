document.addEventListener("DOMContentLoaded", function () {
    // FAQ Toggle
    document.querySelectorAll('.faq-item h3').forEach(item => {
        item.addEventListener('click', function () {
            const answer = this.nextElementSibling;
            answer.style.display = answer.style.display === 'block' ? 'none' : 'block';
        });
    });

    // Gallery Tag Filter
    const tagFilter = document.querySelector('.tag-filter select');
    tagFilter.addEventListener('change', function () {
        const selectedTag = this.value;
        document.querySelectorAll('.image-card').forEach(card => {
            if (selectedTag === 'all' || card.dataset.tags.includes(selectedTag)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    });

    // Testimonial Sort
    document.getElementById('sort-date').addEventListener('click', function () {
        // Sort logic for date
    });

    document.getElementById('sort-rating').addEventListener('click', function () {
        // Sort logic for rating
    });

    // Testimonial Filter
    const testimonialFilter = document.querySelector('.testimonial-filter select');
    testimonialFilter.addEventListener('change', function () {
        const selectedTreatment = this.value;
        document.querySelectorAll('.testimonial').forEach(testimonial => {
            if (selectedTreatment === 'all' || testimonial.dataset.treatment.includes(selectedTreatment)) {
                testimonial.style.display = 'block';
            } else {
                testimonial.style.display = 'none';
            }
        });
    });
});