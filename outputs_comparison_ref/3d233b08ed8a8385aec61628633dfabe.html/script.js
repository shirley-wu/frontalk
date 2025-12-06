function showRegionData(region) {
    const regionArticles = document.getElementById('region-articles');
    regionArticles.innerHTML = `<p>Articles and statistics for ${region}.</p>`;
}

function searchThreads() {
    const input = document.getElementById('search-bar').value.toLowerCase();
    const threads = document.querySelectorAll('.thread-card');
    let found = false;

    threads.forEach(thread => {
        const keywords = thread.getAttribute('data-keywords');
        if (keywords.toLowerCase().includes(input)) {
            thread.style.display = 'block';
            found = true;
        } else {
            thread.style.display = 'none';
        }
    });

    document.getElementById('no-results').style.display = found ? 'none' : 'block';
}

function filterNews() {
    const category = document.getElementById('news-category').value;
    const newsItems = document.querySelectorAll('.news-item');

    newsItems.forEach(item => {
        const itemCategory = item.getAttribute('data-category');
        if (category === 'all' || itemCategory === category) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

function updateCharts() {
    // Placeholder function for updating charts based on time frame
    console.log('Charts updated for the selected time frame.');
}

function compareRegions() {
    // Placeholder function for comparing regions
    console.log('Comparing selected regions.');
}