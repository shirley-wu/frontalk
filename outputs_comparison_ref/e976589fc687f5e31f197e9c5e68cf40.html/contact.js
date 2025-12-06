document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('contact-form');
    const submissionMessage = document.getElementById('submission-message');

    form.addEventListener('submit', function(event) {
        event.preventDefault();
        submissionMessage.textContent = "Thank you for your message! We will get back to you shortly.";
    });

    const faqItems = document.querySelectorAll('.faq-item h3');
    faqItems.forEach(item => {
        item.addEventListener('click', function() {
            const answer = this.nextElementSibling;
            answer.style.display = answer.style.display === 'block' ? 'none' : 'block';
        });
    });
});