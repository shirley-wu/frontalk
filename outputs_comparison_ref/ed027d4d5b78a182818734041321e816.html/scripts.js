document.querySelectorAll('.faq-question').forEach(item => {
    item.addEventListener('click', event => {
        const answer = item.nextElementSibling;
        answer.style.display = answer.style.display === 'block' ? 'none' : 'block';
    });
});