document.addEventListener('DOMContentLoaded', function() {
    let currentIndex = 0;
    const posts = document.querySelectorAll('.post');
    const totalPosts = posts.length;

    function rotatePosts() {
        posts.forEach((post, index) => {
            post.style.transform = `translateX(${(index - currentIndex) * 100}%)`;
        });
    }

    function showNextPost() {
        currentIndex = (currentIndex + 1) % totalPosts;
        rotatePosts();
    }

    function showPrevPost() {
        currentIndex = (currentIndex - 1 + totalPosts) % totalPosts;
        rotatePosts();
    }

    document.querySelector('.next').addEventListener('click', showNextPost);
    document.querySelector('.prev').addEventListener('click', showPrevPost);

    setInterval(showNextPost, 10000); // Rotate every 10 seconds

    rotatePosts();
});