function calculateSavings() {
    const energyUsage = document.getElementById('energyUsage').value;
    const alternativeSource = document.getElementById('alternativeSource').value;
    let savings = 0;

    switch (alternativeSource) {
        case 'solar':
            savings = energyUsage * 0.2;
            break;
        case 'wind':
            savings = energyUsage * 0.25;
            break;
        case 'biomass':
            savings = energyUsage * 0.15;
            break;
    }

    document.getElementById('results').innerHTML = `<p>Estimated Savings: ${savings} kWh</p>`;
}

document.getElementById('compareButton').addEventListener('click', () => {
    alert('Comparison feature coming soon!');
});