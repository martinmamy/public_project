document.addEventListener("DOMContentLoaded", function () {

    const themeToggle = document.getElementById('theme-toggle');
    const root = document.documentElement;

    if (!themeToggle) return;

    // set correct button label immediately
    const theme = root.getAttribute('data-theme');

    themeToggle.textContent =
        theme === 'dark' ? '☀️ Theme' : '🌙 Theme';

    themeToggle.addEventListener('click', () => {

        const newTheme =
            root.getAttribute('data-theme') === 'dark'
                ? 'light'
                : 'dark';

        root.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);

        themeToggle.textContent =
            newTheme === 'dark' ? '☀️ Theme' : '🌙 Theme';
    });

});