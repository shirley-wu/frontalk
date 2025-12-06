let currentBannerIndex = 0;
showSlides(currentBannerIndex);

function showSlides(index) {
    const slides = document.querySelectorAll('.banner-slide');
    const dots = document.querySelectorAll('.dot');
    if (index >= slides.length) currentBannerIndex = 0;
    if (index < 0) currentBannerIndex = slides.length - 1;
    slides.forEach((slide, i) => {
        slide.style.display = i === currentBannerIndex ? 'block' : 'none';
    });
    dots.forEach((dot, i) => {
        dot.className = i === currentBannerIndex ? 'dot active' : 'dot';
    });
}

function nextSlide() {
    showSlides(++currentBannerIndex);
}

function previousSlide() {
    showSlides(--currentBannerIndex);
}

function currentSlide(index) {
    showSlides(currentBannerIndex = index);
}

document.querySelector('.subscription-form form').addEventListener('submit', function(event) {
    event.preventDefault();
    document.getElementById('subscription-confirmation').style.display = 'block';
});