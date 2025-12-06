document.getElementById('newsletterForm').addEventListener('submit', function(event) {
    event.preventDefault();
    document.getElementById('newsletterConfirmation').classList.remove('hidden');
});