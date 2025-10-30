document.querySelector('.vote-button').addEventListener('click', function() {
    let voteCount = document.getElementById('vote-count');
    let currentVotes = parseInt(voteCount.textContent);
    voteCount.textContent = currentVotes + 1;
    document.getElementById('vote-message').textContent = "Thank you for voting!";
});