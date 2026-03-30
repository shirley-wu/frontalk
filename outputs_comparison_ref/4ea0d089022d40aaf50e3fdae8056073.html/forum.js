const threads = document.querySelectorAll('.thread');
threads.forEach(thread => {
    thread.addEventListener('mouseover', () => {
        thread.style.fontSize = '1.1em';
        thread.style.transition = 'font-size 0.3s';
    });
    thread.addEventListener('mouseout', () => {
        thread.style.fontSize = '1em';
    });
});