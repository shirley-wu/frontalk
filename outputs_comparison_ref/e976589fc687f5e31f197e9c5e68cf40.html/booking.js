document.addEventListener('DOMContentLoaded', function() {
    const seats = document.querySelectorAll('.seat');
    const confirmationMessage = document.getElementById('confirmation-message');

    seats.forEach(seat => {
        seat.addEventListener('click', function() {
            if (seat.classList.contains('available')) {
                seat.classList.toggle('selected');
            }
        });

        seat.addEventListener('mouseover', function() {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.innerHTML = `Seat: ${seat.dataset.seat}, Price: ${seat.dataset.price}`;
            seat.appendChild(tooltip);
        });

        seat.addEventListener('mouseout', function() {
            const tooltip = seat.querySelector('.tooltip');
            if (tooltip) {
                seat.removeChild(tooltip);
            }
        });
    });

    document.getElementById('confirm-purchase').addEventListener('click', function() {
        confirmationMessage.textContent = "Your seats have been successfully booked!";
    });
});