document.addEventListener("DOMContentLoaded", function () {
    const sliders = document.querySelectorAll(".slider");
    let currentSlider = 0;

    function showSlider(index) {
        sliders.forEach((slider, i) => {
            slider.style.opacity = i === index ? "1" : "0";
        });
    }

    document.querySelector(".right-arrow").addEventListener("click", function () {
        currentSlider = (currentSlider + 1) % sliders.length;
        showSlider(currentSlider);
    });

    document.querySelector(".left-arrow").addEventListener("click", function () {
        currentSlider = (currentSlider - 1 + sliders.length) % sliders.length;
        showSlider(currentSlider);
    });

    showSlider(currentSlider);

    const quizForm = document.getElementById("style-quiz");
    const quizResults = document.getElementById("quiz-results");
    const retakeQuizButton = document.getElementById("retake-quiz");

    quizForm.addEventListener("submit", function (event) {
        event.preventDefault();
        quizForm.style.display = "none";
        quizResults.style.display = "block";
    });

    retakeQuizButton.addEventListener("click", function () {
        quizForm.style.display = "block";
        quizResults.style.display = "none";
    });

    const sendRecommendationsButton = document.getElementById("send-recommendations");
    sendRecommendationsButton.addEventListener("click", function () {
        const email = document.getElementById("email").value;
        if (email) {
            alert(`Recommendations sent to ${email}`);
        } else {
            alert("Please enter a valid email address.");
        }
    });
});