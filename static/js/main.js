// Dark mode toggle
(function () {
  const root = document.documentElement;
  const toggle = document.getElementById("theme-toggle");
  const saved = localStorage.getItem("edugenie-theme");
  if (saved) root.setAttribute("data-theme", saved);

  function updateIcon() {
    const theme = root.getAttribute("data-theme") || "light";
    if (toggle) toggle.textContent = theme === "dark" ? "☀️" : "🌙";
  }
  updateIcon();

  if (toggle) {
    toggle.addEventListener("click", () => {
      const current = root.getAttribute("data-theme") || "light";
      const next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      localStorage.setItem("edugenie-theme", next);
      updateIcon();
    });
  }
})();

// Helpers shared by pages
function renderMarkdown(text) {
  try {
    return marked.parse(text);
  } catch (e) {
    return text;
  }
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}
