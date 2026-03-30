function login() {
    document.getElementById('login-section').style.display = 'none';
    document.getElementById('dashboard-section').style.display = 'block';
}

function logout() {
    document.getElementById('login-section').style.display = 'block';
    document.getElementById('dashboard-section').style.display = 'none';
}

function selectTheme(theme) {
    alert(`Theme changed to ${theme}!`);
}