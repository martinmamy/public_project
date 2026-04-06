// theme.js

document.addEventListener("DOMContentLoaded", function () {

// THEME TOGGLE
const themeToggle = document.getElementById('theme-toggle');
const currentTheme = localStorage.getItem('theme');

// Apply saved theme on page load
if (currentTheme) {
    document.documentElement.setAttribute('data-theme', currentTheme);
    themeToggle.textContent = currentTheme === 'dark' ? '☀️ Theme' : '🌙 Theme';
}

// Toggle theme on click
themeToggle.addEventListener('click', () => {
    const theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    themeToggle.textContent = theme === 'dark' ? '☀️ Theme' : '🌙 Theme';
});

});