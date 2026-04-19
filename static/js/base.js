
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

function getSelectedProjectId() {
    return $('#id_proj_id').val() || '';
}

function renderWorkspacePlaceholder(target, message, tone = 'info') {
    $(target).html(`<div class="alert alert-${tone} mt-3 mb-0">${message}</div>`);
}

function loadWorkspaceTab(buttonElement, extraData = {}) {
    const $button = $(buttonElement);
    const url = $button.data('url');
    const target = $button.attr('data-bs-target');

    if (!url || url === '#' || !target) {
        return;
    }

    const projectId = getSelectedProjectId();
    if (!projectId) {
        renderWorkspacePlaceholder(target, 'Select a project in the Project Data form before loading this tab.', 'warning');
        return;
    }

    $(target).html('<div class="text-muted mt-3">Loading...</div>');
    $.ajax({
        url: url,
        type: 'GET',
        data: { project_id: projectId, ...extraData },
        success: function (html) {
            $(target).html(html);
        },
        error: function (xhr) {
            let errorMessage = 'Failed to load project data for this tab.';
            if (xhr.responseJSON && xhr.responseJSON.error) {
                errorMessage = xhr.responseJSON.error;
            }
            renderWorkspacePlaceholder(target, errorMessage, 'danger');
        }
    });
}

window.loadWorkspaceTab = loadWorkspaceTab;

window.resetWorkspaceTabContent = function () {
    renderWorkspacePlaceholder(
        '#result-tab-pane',
        'Select a project in the Project Data form, then open this tab to load stored calculation results.'
    );
    renderWorkspacePlaceholder(
        '#boq-tab-pane',
        'Select a project in the Project Data form, then open this tab to load stored BOQ data.'
    );
};

// Click-driven load is more reliable here than depending only on Bootstrap tab events.
$(document).on('click', 'button.nav-link[data-url]', debounce(function () {
    loadWorkspaceTab(this);
}, 150));

$(document).on('submit', '#boq-line-filter-form', function (e) {
    e.preventDefault();
    const activeButton = document.querySelector('button.nav-link#boq-tab');
    const formData = Object.fromEntries(new FormData(this).entries());
    loadWorkspaceTab(activeButton, formData);
});

$(document).on('click', '#boq-line-filter-reset', function () {
    const activeButton = document.querySelector('button.nav-link#boq-tab');
    loadWorkspaceTab(activeButton);
});


