// Banner image rotation
let bannerIndex = 0;
const banners = [
    { image: '../../../../placeholder/placeholder.png', text: 'Paris', date: 'Visited: March 2023' },
    { image: '../../../../placeholder/placeholder.png', text: 'New York', date: 'Visited: April 2023' },
    { image: '../../../../placeholder/placeholder.png', text: 'Tokyo', date: 'Visited: May 2023' },
    { image: '../../../../placeholder/placeholder.png', text: 'Sydney', date: 'Visited: June 2023' },
    { image: '../../../../placeholder/placeholder.png', text: 'Cape Town', date: 'Visited: July 2023' }
];

function rotateBanner() {
    bannerIndex = (bannerIndex + 1) % banners.length;
    const banner = document.querySelector('.banner img');
    const overlayText = document.querySelector('.overlay-text');
    banner.src = banners[bannerIndex].image;
    overlayText.innerHTML = `<h2>${banners[bannerIndex].text}</h2><p>${banners[bannerIndex].date}</p>`;
    const dots = document.querySelectorAll('.dot');
    dots.forEach(dot => dot.classList.remove('active'));
    dots[bannerIndex].classList.add('active');
}

setInterval(rotateBanner, 3000);

// Lightbox functionality
let currentImageIndex = 0;

function openLightbox(index) {
    currentImageIndex = index;
    const lightbox = document.getElementById('lightbox');
    const lightboxImg = document.getElementById('lightbox-img');
    lightbox.style.display = 'flex';
    lightboxImg.src = '../../../../placeholder/placeholder.png';
}

function closeLightbox() {
    document.getElementById('lightbox').style.display = 'none';
}

function prevImage() {
    currentImageIndex = (currentImageIndex - 1 + 5) % 5;
    document.getElementById('lightbox-img').src = '../../../../placeholder/placeholder.png';
}

function nextImage() {
    currentImageIndex = (currentImageIndex + 1) % 5;
    document.getElementById('lightbox-img').src = '../../../../placeholder/placeholder.png';
}

// Budget Estimator
document.getElementById('calculate-budget').addEventListener('click', function() {
    const transportation = parseFloat(document.getElementById('transportation').value) || 0;
    const accommodation = parseFloat(document.getElementById('accommodation').value) || 0;
    const activities = parseFloat(document.getElementById('activities').value) || 0;
    const totalBudget = transportation + accommodation + activities;
    document.getElementById('budget-result').innerText = `Total Budget: $${totalBudget}`;
});

// Quiz functionality
let score = 0;

function checkAnswer(button, isCorrect) {
    if (isCorrect) {
        score++;
        button.style.backgroundColor = 'green';
    } else {
        button.style.backgroundColor = 'red';
    }
    button.disabled = true;
}

function showResults() {
    alert(`Your score is: ${score}`);
    score = 0;
    const buttons = document.querySelectorAll('.question button');
    buttons.forEach(button => {
        button.disabled = false;
        button.style.backgroundColor = '';
    });
}