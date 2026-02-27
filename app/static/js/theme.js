(function () {
  const key = "theme-preference";
  const media = window.matchMedia("(prefers-color-scheme: dark)");

  function getPreferredTheme() {
    const saved = localStorage.getItem(key);
    if (saved === "dark" || saved === "light") return saved;
    return "dark";
  }

  function setTheme(theme) {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");

    const btn = document.getElementById("themeToggle");
    if (btn) btn.textContent = theme === "dark" ? "Light Mode" : "Dark Mode";
  }

  let theme = getPreferredTheme();
  setTheme(theme);

  media.addEventListener("change", (event) => {
    if (localStorage.getItem(key)) return;
    theme = event.matches ? "dark" : "light";
    setTheme(theme);
  });

  window.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("themeToggle");
    setTheme(theme);
    if (!btn) return;

    btn.addEventListener("click", () => {
      theme = theme === "dark" ? "light" : "dark";
      localStorage.setItem(key, theme);
      setTheme(theme);
    });
  });
})();
