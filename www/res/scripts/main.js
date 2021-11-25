
window.addEventListener("DOMContentLoaded", () => {
    const status = parseInt(document.title.split(' ')[0]) || 200;
    if (window.location.pathname.startsWith('/calendar/') && status === 200) {
        const cal = new Calendar(document.getElementsByTagName("main")[0]);
    }
});
