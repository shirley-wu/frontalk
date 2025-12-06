document.getElementById('bookingForm').addEventListener('submit', function(event) {
    event.preventDefault();
    const serviceType = document.getElementById('serviceType').value;
    const date = document.getElementById('date').value;
    const contactInfo = document.getElementById('contactInfo').value;

    alert(`Confirmation Email Sent!\nService Type: ${serviceType}\nDate: ${date}\nContact Info: ${contactInfo}`);

    window.location.href = 'confirmation.html';
});