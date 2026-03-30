document.querySelector('.filter-button').addEventListener('click', function() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar.style.left === '0px') {
        sidebar.style.left = '-250px';
    } else {
        sidebar.style.left = '0px';
    }
});

// Slideshow functionality
let slideIndex = 0;
const slides = document.querySelectorAll('.slideshow img');
setInterval(() => {
    slides.forEach((slide, index) => {
        slide.style.display = index === slideIndex ? 'block' : 'none';
    });
    slideIndex = (slideIndex + 1) % slides.length;
}, 3000);