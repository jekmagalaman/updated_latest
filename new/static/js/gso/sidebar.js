document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.getElementById("sidebar");
    const hamburger = document.getElementById("sidebarToggle");
    const body = document.body;

    // Load collapsed state from localStorage (default: true on desktop)
    let isCollapsed = localStorage.getItem("sidebarCollapsed") === "true";
    if (window.innerWidth > 768 && isCollapsed) {
        sidebar.classList.add("collapsed");
    }

    // Hamburger click toggles collapsed state
    hamburger.addEventListener("click", () => {
        if (window.innerWidth <= 768) {
            sidebar.classList.toggle("show");
            body.classList.toggle("sidebar-open");
        } else {
            sidebar.classList.toggle("collapsed");
            isCollapsed = sidebar.classList.contains("collapsed");
            localStorage.setItem("sidebarCollapsed", isCollapsed);
        }
    });

    // Click outside on mobile closes sidebar
    body.addEventListener("click", (e) => {
        if (
            window.innerWidth <= 768 &&
            sidebar.classList.contains("show") &&
            !sidebar.contains(e.target) &&
            !hamburger.contains(e.target)
        ) {
            sidebar.classList.remove("show");
            body.classList.remove("sidebar-open");
        }
    });

    // Handle window resize
    function handleResize() {
        if (window.innerWidth <= 768) {
            sidebar.classList.remove("collapsed", "show");
            body.classList.remove("sidebar-open");
        } else if (window.innerWidth <= 1024) {
            sidebar.classList.add("collapsed");
            sidebar.classList.remove("show");
            body.classList.remove("sidebar-open");
            isCollapsed = true;
            localStorage.setItem("sidebarCollapsed", isCollapsed);
        } else {
            if (localStorage.getItem("sidebarCollapsed") === "true") {
                sidebar.classList.add("collapsed");
                sidebar.classList.remove("show");
            } else {
                sidebar.classList.remove("collapsed", "show");
            }
            body.classList.remove("sidebar-open");
        }
    }

    handleResize();
    window.addEventListener("resize", handleResize);
});
