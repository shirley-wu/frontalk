document.addEventListener('DOMContentLoaded', function() {
    // Carousel logic for highlights and featured articles
    let carouselIndex = 0;
    const highlights = document.querySelectorAll('.highlight');
    const articles = document.querySelectorAll('.article');

    function showHighlight(index) {
        highlights.forEach((highlight, i) => {
            highlight.style.display = i === index ? 'block' : 'none';
        });
    }

    function showArticle(index) {
        articles.forEach((article, i) => {
            article.style.display = i === index ? 'block' : 'none';
        });
    }

    function nextHighlight() {
        carouselIndex = (carouselIndex + 1) % highlights.length;
        showHighlight(carouselIndex);
    }

    function nextArticle() {
        carouselIndex = (carouselIndex + 1) % articles.length;
        showArticle(carouselIndex);
    }

    setInterval(nextHighlight, 5000);
    setInterval(nextArticle, 5000);

    showHighlight(carouselIndex);
    showArticle(carouselIndex);
});