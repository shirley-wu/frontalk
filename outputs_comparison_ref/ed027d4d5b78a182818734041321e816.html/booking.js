document.querySelectorAll('.date').forEach(date => {
    date.addEventListener('click', () => {
        document.querySelectorAll('.date').forEach(d => d.classList.remove('selected'));
        date.classList.add('selected');
        document.getElementById('confirmation').innerText = `You have selected ${date.innerText} for your consultation.`;
    });
});