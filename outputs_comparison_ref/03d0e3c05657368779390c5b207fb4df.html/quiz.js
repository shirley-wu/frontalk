document.getElementById('quiz-form').addEventListener('submit', function(event) {
    event.preventDefault();
    let score = 0;
    const answers = {
        q1: 'b',
        q2: 'b'
    };
    const userAnswers = new FormData(event.target);
    for (let [question, answer] of userAnswers.entries()) {
        if (answer === answers[question]) {
            score++;
        }
    }
    document.getElementById('quiz-result').textContent = `You scored ${score} out of 2!`;
});