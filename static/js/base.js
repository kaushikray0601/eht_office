
//JavaScript to toggle sidebar -->

document.addEventListener("DOMContentLoaded", function () {
    const toggleSidebarBtn = document.getElementById('toggleSidebar');
    if (toggleSidebarBtn) {
        toggleSidebarBtn.addEventListener('click', function () {
            let sidebar = document.getElementById('sidebar');
            let mainContent = document.getElementById('mainContent');
            sidebar.classList.toggle('collapsed');
            sidebar.classList.toggle('expanded');
            mainContent.classList.toggle('collapsed');
            mainContent.classList.toggle('expanded');
        });
    }
});


function debounce(func, delay) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), delay);
    };
}
// JavaScript to control Tab -->
$(document).on('click', '.nav-link', debounce(function (e) {
    e.preventDefault();
    const url = $(this).data('url');
    if (!url || url === undefined || url === '#' || url === '' || url === null) {       
        return; // Stop execution if URL is undefined
    }
    $('#tabContent').load(url);
    //alert('clicked');
}, 300));




