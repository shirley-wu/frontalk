document.addEventListener('DOMContentLoaded', function() {
    let currentIndex = 0;
    const items = document.querySelectorAll('.carousel-item');
    const totalItems = items.length;

    function showItem(index) {
        items.forEach((item, i) => {
            item.style.transform = `translateX(${100 * (i - index)}%)`;
        });
    }

    function nextItem() {
        currentIndex = (currentIndex + 1) % totalItems;
        showItem(currentIndex);
    }

    function previousItem() {
        currentIndex = (currentIndex - 1 + totalItems) % totalItems;
        showItem(currentIndex);
    }

    setInterval(nextItem, 3000);

    const compareButtons = document.querySelectorAll('.compare');
    const comparisonTable = document.getElementById('comparison-table');
    let selectedServices = [];

    compareButtons.forEach(button => {
        button.addEventListener('click', function() {
            const serviceId = this.getAttribute('data-service');
            if (!selectedServices.includes(serviceId)) {
                selectedServices.push(serviceId);
            }
            if (selectedServices.length > 3) {
                selectedServices.shift();
            }
            updateComparisonTable();
        });
    });

    function updateComparisonTable() {
        if (selectedServices.length > 0) {
            comparisonTable.style.display = 'block';
            comparisonTable.innerHTML = '<h3>Comparison Table</h3><table><tr><th>Service</th><th>Benefits</th><th>Price</th></tr>';
            selectedServices.forEach(serviceId => {
                const serviceElement = document.getElementById(`service${serviceId}`);
                const serviceName = serviceElement.querySelector('h2').innerText;
                const benefits = serviceElement.querySelector('p:nth-of-type(2)').innerText;
                const price = serviceElement.querySelector('p:nth-of-type(3)').innerText;
                comparisonTable.innerHTML += `<tr><td>${serviceName}</td><td>${benefits}</td><td>${price}</td></tr>`;
            });
            comparisonTable.innerHTML += '</table>';
        } else {
            comparisonTable.style.display = 'none';
        }
    }

    const faqItems = document.querySelectorAll('.faq-item h3');
    faqItems.forEach(item => {
        item.addEventListener('click', function() {
            const answer = this.nextElementSibling;
            answer.style.display = answer.style.display === 'block' ? 'none' : 'block';
        });
    });
});