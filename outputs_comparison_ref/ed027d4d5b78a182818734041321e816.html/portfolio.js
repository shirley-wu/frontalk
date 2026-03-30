function filterProjects(type) {
    const projects = document.querySelectorAll('.project-item');
    projects.forEach(project => {
        if (type === 'all' || project.classList.contains(type)) {
            project.style.display = 'block';
        } else {
            project.style.display = 'none';
        }
    });
}