function initMap() {
    const map = new google.maps.Map(document.getElementById('map'), {
        zoom: 2,
        center: { lat: 20, lng: 0 }
    });

    const plants = [
        { lat: 40.7128, lng: -74.0060, name: "New York Plant", status: "Existing" },
        { lat: 34.0522, lng: -118.2437, name: "Los Angeles Plant", status: "Planned" },
        { lat: 51.5074, lng: -0.1278, name: "London Plant", status: "Existing" },
        { lat: 35.6895, lng: 139.6917, name: "Tokyo Plant", status: "Planned" },
        { lat: -33.8688, lng: 151.2093, name: "Sydney Plant", status: "Existing" }
    ];

    plants.forEach(plant => {
        const marker = new google.maps.Marker({
            position: { lat: plant.lat, lng: plant.lng },
            map: map,
            title: plant.name,
            icon: plant.status === "Existing" ? 'green-dot.png' : 'blue-dot.png'
        });

        const infoWindow = new google.maps.InfoWindow({
            content: `<h3>${plant.name}</h3><p>Status: ${plant.status}</p>`
        });

        marker.addListener('mouseover', () => {
            infoWindow.open(map, marker);
        });
    });
}

window.onload = initMap;