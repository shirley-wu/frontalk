document.addEventListener('DOMContentLoaded', function() {
    const carouselItems = document.querySelectorAll('.carousel-item');
    let currentIndex = 0;

    function showCarouselItem(index) {
        carouselItems.forEach((item, i) => {
            item.style.transform = `translateX(${(i - index) * 100}%)`;
        });
    }

    document.querySelector('.carousel-nav.left').addEventListener('click', function() {
        currentIndex = (currentIndex === 0) ? carouselItems.length - 1 : currentIndex - 1;
        showCarouselItem(currentIndex);
    });

    document.querySelector('.carousel-nav.right').addEventListener('click', function() {
        currentIndex = (currentIndex === carouselItems.length - 1) ? 0 : currentIndex + 1;
        showCarouselItem(currentIndex);
    });

    setInterval(() => {
        currentIndex = (currentIndex === carouselItems.length - 1) ? 0 : currentIndex + 1;
        showCarouselItem(currentIndex);
    }, 5000);
});