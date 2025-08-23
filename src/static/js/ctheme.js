document.addEventListener("DOMContentLoaded", () => {
    const themeToggle = document.getElementById("theme-toggle");
    const themeIcon = document.getElementById("theme-icon");
    const html = document.documentElement;

    const updateTitleColors = () => {
        const isDarkMode = html.dataset.theme === "dark";

        const titlesToChange = document.querySelectorAll(".theme-aware-title");

        titlesToChange.forEach(title => {
            if (isDarkMode) {
                title.classList.remove("has-text-dark");
                title.classList.add("has-text-light");
            } else {
                title.classList.remove("has-text-light");
                title.classList.add("has-text-dark");
            }
        });
    };

    const savedTheme = localStorage.getItem("theme");
    const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

    if (savedTheme) {
        html.dataset.theme = savedTheme;
    } else {
        html.dataset.theme = systemPrefersDark ? "dark" : "light";
    }

    const updateIcon = () => {
        if (html.dataset.theme === "dark") {
            themeIcon.classList.replace("fa-moon", "fa-sun");
        } else {
            themeIcon.classList.replace("fa-sun", "fa-moon");
        }
    };

    themeToggle.addEventListener("click", () => {
        html.dataset.theme = html.dataset.theme === "light" ? "dark" : "light";
        localStorage.setItem("theme", html.dataset.theme);
        updateIcon();
        updateTitleColors(); 
    });
    updateIcon();
    updateTitleColors();
});