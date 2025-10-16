document.addEventListener('DOMContentLoaded', () => {
    const liveChatButton = document.getElementById('liveChat');
    const chatBox = document.getElementById('chat-box');
    const endChatButton = document.getElementById('end-chat');
    const feedbackBox = document.getElementById('feedback-box');
    const submitFeedbackButton = document.getElementById('submit-feedback');

    liveChatButton.addEventListener('click', () => {
        chatBox.classList.toggle('hidden');
    });

    endChatButton.addEventListener('click', () => {
        chatBox.classList.add('hidden');
        feedbackBox.classList.remove('hidden');
    });

    submitFeedbackButton.addEventListener('click', () => {
        feedbackBox.classList.add('hidden');
        alert('Thank you for your feedback!');
    });

    const appointmentForm = document.getElementById('appointment-form');
    const steps = document.querySelectorAll('.step');
    const stepContents = document.querySelectorAll('.step-content');
    let currentStep = 0;

    appointmentForm.addEventListener('submit', (e) => {
        e.preventDefault();
        if (currentStep < steps.length - 1) {
            steps[currentStep].classList.add('completed');
            stepContents[currentStep].classList.add('hidden');
            currentStep++;
            stepContents[currentStep].classList.remove('hidden');
        } else {
            // Send confirmation email (pseudo-code)
            const email = document.getElementById('email').value;
            const therapist = document.getElementById('therapist').value;
            const timeSlot = document.getElementById('time-slot').value;
            alert(`Appointment confirmed with ${therapist} at ${timeSlot}. Confirmation email sent to ${email}.`);
        }
    });

    const saveFavoriteButtons = document.querySelectorAll('.save-favorite');
    const favoritesSection = document.querySelector('.favorites-section');
    const favoriteItems = document.querySelector('.favorite-items');

    saveFavoriteButtons.forEach(button => {
        button.addEventListener('click', () => {
            const resourceItem = button.parentElement.cloneNode(true);
            resourceItem.querySelector('.save-favorite').remove();
            favoriteItems.appendChild(resourceItem);
            favoritesSection.classList.add('active');
        });
    });

    const searchBar = document.getElementById('search-bar');
    const resourceItems = document.querySelectorAll('.resource-item');

    searchBar.addEventListener('input', () => {
        const query = searchBar.value.toLowerCase();
        resourceItems.forEach(item => {
            const title = item.querySelector('h4').textContent.toLowerCase();
            if (title.includes(query)) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    });

    const sortByDateButton = document.getElementById('sort-date');
    const sortByRelevanceButton = document.getElementById('sort-relevance');

    sortByDateButton.addEventListener('click', () => {
        alert('Sorting by date not implemented.'); // Placeholder for sorting logic
    });

    sortByRelevanceButton.addEventListener('click', () => {
        alert('Sorting by relevance not implemented.'); // Placeholder for sorting logic
    });
});