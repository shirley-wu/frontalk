document.getElementById('contact-form').addEventListener('submit', function(event) {
    event.preventDefault();
    document.getElementById('form-confirmation').innerText = 'Thank you for your inquiry. We will get back to you soon!';
    this.reset();
});