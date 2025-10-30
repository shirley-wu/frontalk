document.addEventListener("DOMContentLoaded", function() {
    // Placeholder for user authentication check
    const isLoggedIn = false; // Change this to true to simulate a logged-in user

    const profileLink = document.getElementById("profile-link");
    if (isLoggedIn) {
        profileLink.style.display = "block";
    }
});