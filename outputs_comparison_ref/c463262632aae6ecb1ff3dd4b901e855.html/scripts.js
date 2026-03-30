document.addEventListener('DOMContentLoaded', function() {
    const calendar = document.getElementById('calendar');
    const events = [
        { date: '2023-11-01', name: 'Concert 1', type: 'concert', icon: '🎤' },
        { date: '2023-11-02', name: 'Sport 1', type: 'sports', icon: '🏀' },
        { date: '2023-11-03', name: 'Theater 1', type: 'theater', icon: '🎭' },
        { date: '2023-11-04', name: 'Concert 2', type: 'concert', icon: '🎤' },
        { date: '2023-11-05', name: 'Sport 2', type: 'sports', icon: '🏀' },
    ];

    events.forEach(event => {
        const eventDiv = document.createElement('div');
        eventDiv.innerHTML = `<span>${event.icon}</span> ${event.name}`;
        eventDiv.style.backgroundColor = getColorByType(event.type);
        eventDiv.onclick = () => location.href = `event-details.html?event=${event.name}`;
        calendar.appendChild(eventDiv);
    });

    function getColorByType(type) {
        switch(type) {
            case 'concert': return '#ffcccb';
            case 'sports': return '#ccffcc';
            case 'theater': return '#ccccff';
            default: return '#fff';
        }
    }
});