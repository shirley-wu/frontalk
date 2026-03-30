let currentSlideIndex = 0;

function showSlide(index) {
    const slides = document.querySelectorAll('.carousel-item');
    if (index >= slides.length) currentSlideIndex = 0;
    if (index < 0) currentSlideIndex = slides.length - 1;
    slides.forEach((slide, i) => {
        slide.style.transform = `translateX(${(i - currentSlideIndex) * 100}%)`;
    });
}

function nextSlide() {
    currentSlideIndex++;
    showSlide(currentSlideIndex);
}

function prevSlide() {
    currentSlideIndex--;
    showSlide(currentSlideIndex);
}

function currentSlide(index) {
    currentSlideIndex = index - 1;
    showSlide(currentSlideIndex);
}

document.querySelector('.arrow.left').addEventListener('click', prevSlide);
document.querySelector('.arrow.right').addEventListener('click', nextSlide);
document.querySelectorAll('.dot').forEach((dot, index) => {
    dot.addEventListener('click', () => currentSlide(index + 1));
});

showSlide(currentSlideIndex);