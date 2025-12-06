document.addEventListener('DOMContentLoaded', function () {
    const faqItems = document.querySelectorAll('.faq-item .faq-question');
    faqItems.forEach(item => {
        item.addEventListener('click', function () {
            const answer = this.nextElementSibling;
            answer.style.display = answer.style.display === 'block' ? 'none' : 'block';
        });
    });

    const serviceFilter = document.getElementById('service-filter');
    const serviceCards = document.querySelectorAll('.service-card');

    serviceFilter.addEventListener('change', function () {
        const category = this.value;
        serviceCards.forEach(card => {
            if (category === 'all' || card.dataset.category === category) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    });

    let zoomLevel = 1;
    const previewImage = document.getElementById('design-preview-image');
    const zoomInButton = document.getElementById('zoom-in');
    const zoomOutButton = document.getElementById('zoom-out');

    zoomInButton.addEventListener('click', function () {
        zoomLevel += 0.1;
        previewImage.style.transform = `scale(${zoomLevel})`;
    });

    zoomOutButton.addEventListener('click', function () {
        zoomLevel = Math.max(1, zoomLevel - 0.1);
        previewImage.style.transform = `scale(${zoomLevel})`;
    });
});