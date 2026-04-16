document.addEventListener("DOMContentLoaded", function () {

    const themeToggle = document.getElementById('theme-toggle');
    const root = document.documentElement;

    // Get saved theme OR fallback to system preference
    let theme = localStorage.getItem('theme');

    if (!theme) {
        theme = window.matchMedia('(prefers-color-scheme: dark)').matches
            ? 'dark'
            : 'light';
    }

    // Apply theme globally (works for ALL users)
    root.setAttribute('data-theme', theme);

    // Update button text ONLY if it exists (logged-in users)
    if (themeToggle) {
        themeToggle.textContent =
            theme === 'dark' ? '☀️ Theme' : '🌙 Theme';

        // Attach event safely
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
    }

});