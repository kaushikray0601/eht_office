
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

function boqLineDetailFormatter(index, row) {
    const lineId = row['line-id'] || '';
    return `
        <div class="boq-inline-detail" data-line-id="${lineId}">
            <div class="text-muted small py-2">Loading BOQ details...</div>
        </div>
    `;
}

window.boqLineDetailFormatter = boqLineDetailFormatter;

function initializeBootstrapTableDefaults() {
    if (!$.fn.bootstrapTable || $.fn.bootstrapTable._ehtDefaultsApplied) {
        return;
    }

    $.fn.bootstrapTable.defaults.locale = 'en-US';
    $.fn.bootstrapTable.defaults.buttonsPrefix = 'btn';
    $.fn.bootstrapTable.defaults.buttonsClass = 'outline-secondary';
    $.fn.bootstrapTable.defaults.iconsPrefix = 'bi';
    $.fn.bootstrapTable.defaults.icons = {
        paginationSwitchDown: 'bi-caret-down-fill',
        paginationSwitchUp: 'bi-caret-up-fill',
        refresh: 'bi-arrow-clockwise',
        toggleOff: 'bi-toggle-off',
        toggleOn: 'bi-toggle-on',
        columns: 'bi-layout-three-columns',
        detailOpen: 'bi-plus-square',
        detailClose: 'bi-dash-square',
        fullscreen: 'bi-arrows-fullscreen',
        export: 'bi-download',
    };

    $.fn.bootstrapTable._ehtDefaultsApplied = true;
}

function enhanceBootstrapTableUi(container) {
    $(container).find('.bootstrap-table').each(function () {
        const $wrapper = $(this);
        $wrapper.find('.search input').addClass('form-control form-control-sm');
        $wrapper.find('.page-list select').addClass('form-select form-select-sm');
        $wrapper.find('.fixed-table-toolbar .btn').addClass('btn-sm');
    });
}

function initializeBootstrapTables(container) {
    if (!$.fn.bootstrapTable) {
        return;
    }
    initializeBootstrapTableDefaults();
    $(container).find('table[data-toggle="table"]').each(function () {
        const $table = $(this);
        if ($table.data('bootstrap.table')) {
            $table.bootstrapTable('destroy');
        }
        $table.bootstrapTable();
    });
    enhanceBootstrapTableUi(container);
}

function resetBootstrapTables(container) {
    if (!$.fn.bootstrapTable) {
        return;
    }
    $(container).find('table[data-toggle="table"]').each(function () {
        const $table = $(this);
        if ($table.data('bootstrap.table')) {
            $table.bootstrapTable('resetView');
        }
    });
    enhanceBootstrapTableUi(container);
}

function scrollWorkspaceContentIntoView(target, selector) {
    const root = document.querySelector(target);
    if (!root) {
        return;
    }
    const scrollTarget = selector ? root.querySelector(selector) : root;
    if (!scrollTarget) {
        return;
    }
    requestAnimationFrame(function () {
        scrollTarget.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
}

function loadWorkspaceContent(url, target, extraData = {}, options = {}) {
    if (!url || url === '#' || !target) {
        return;
    }

    const projectId = extraData.project_id || getSelectedProjectId();
    if (!projectId) {
        renderWorkspacePlaceholder(target, 'Select a project in the Project Data form before loading this tab.', 'warning');
        return;
    }

    $(target).html('<div class="text-muted mt-3">Loading...</div>');
    $.ajax({
        url: url,
        type: 'GET',
        data: { ...extraData, project_id: projectId },
        success: function (html) {
            $(target).html(html);
            initializeBootstrapTables(target);
            resetBootstrapTables(target);
            if (window.initializeSldWorkspace) {
                window.initializeSldWorkspace(target);
            }
            if (options.scrollToSelector) {
                scrollWorkspaceContentIntoView(target, options.scrollToSelector);
            }
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

function loadWorkspaceTab(buttonElement, extraData = {}) {
    const $button = $(buttonElement);
    loadWorkspaceContent($button.data('url'), $button.attr('data-bs-target'), extraData);
}

function loadWorkspaceFilterForm(formElement, tabSelector, targetFallback) {
    const activeButton = document.querySelector(tabSelector);
    const formData = Object.fromEntries(new FormData(formElement).entries());
    const url = formElement.dataset.url || (activeButton ? activeButton.dataset.url : '');
    const target = activeButton ? activeButton.getAttribute('data-bs-target') : targetFallback;
    const scrollToSelector = formElement.dataset.scrollTo || '';
    loadWorkspaceContent(url, target, formData, { scrollToSelector: scrollToSelector });
}

window.loadWorkspaceTab = loadWorkspaceTab;

function setSldWorkbenchMode(isActive) {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    if (!sidebar || !mainContent) {
        return;
    }

    if (isActive) {
        if (!sidebar.classList.contains('collapsed')) {
            sidebar.dataset.autoCollapsedBySld = 'true';
            sidebar.classList.add('collapsed');
            sidebar.classList.remove('expanded');
            mainContent.classList.add('collapsed');
            mainContent.classList.remove('expanded');
        }
        document.body.classList.add('sld-workbench-active');
        return;
    }

    document.body.classList.remove('sld-workbench-active');
    document.body.classList.remove('sld-zen-mode');
    if (sidebar.dataset.autoCollapsedBySld === 'true') {
        sidebar.classList.remove('collapsed');
        sidebar.classList.add('expanded');
        mainContent.classList.remove('collapsed');
        mainContent.classList.add('expanded');
        delete sidebar.dataset.autoCollapsedBySld;
    }
}

window.resetWorkspaceTabContent = function () {
    renderWorkspacePlaceholder(
        '#import-input-tab-pane',
        'Select a project in the Project Data form, then open this tab to inspect the imported input data.'
    );
    renderWorkspacePlaceholder(
        '#result-tab-pane',
        'Select a project in the Project Data form, then open this tab to load stored calculation results.'
    );
    renderWorkspacePlaceholder(
        '#cable-schedule-tab-pane',
        'Select a project in the Project Data form, then open this tab to load the active cable schedule.'
    );
    renderWorkspacePlaceholder(
        '#boq-tab-pane',
        'Select a project in the Project Data form, then open this tab to load stored BOQ data.'
    );
    renderWorkspacePlaceholder(
        '#sld-tab-pane',
        'Select a project in the Project Data form, then open this tab to load the stored SLD graph data.'
    );
};

window.initializeBootstrapTables = initializeBootstrapTables;
window.resetBootstrapTables = resetBootstrapTables;

function loadBoqInlineDetail(tableElement, index, row, $detail) {
    const $table = $(tableElement);
    const detailUrl = $table.data('detailUrl');
    const lineId = row['line-id'];
    const projectId = getSelectedProjectId();
    const $container = $detail.find('.boq-inline-detail');

    if (!$container.length || $container.data('loaded') || !detailUrl) {
        return;
    }

    $.ajax({
        url: detailUrl,
        type: 'GET',
        data: { project_id: projectId, line_id: lineId },
        success: function (html) {
            $container.html(html);
            $container.data('loaded', true);
        },
        error: function (xhr) {
            let errorMessage = 'Failed to load BOQ details for this line.';
            if (xhr.responseJSON && xhr.responseJSON.error) {
                errorMessage = xhr.responseJSON.error;
            }
            $container.html(`<div class="alert alert-danger mb-0">${errorMessage}</div>`);
        }
    });
}

// Click-driven load is more reliable here than depending only on Bootstrap tab events.
$(document).on('click', 'button.nav-link[data-url]', debounce(function () {
    setSldWorkbenchMode(this.getAttribute('data-bs-target') === '#sld-tab-pane');
    loadWorkspaceTab(this);
}, 150));

document.addEventListener('shown.bs.tab', function (event) {
    const target = event.target.getAttribute('data-bs-target');
    if (!target) {
        return;
    }
    setSldWorkbenchMode(target === '#sld-tab-pane');
    initializeBootstrapTables(target);
    resetBootstrapTables(target);
});

$(document).on('submit', '#sld-line-filter-form', function (e) {
    e.preventDefault();
    loadWorkspaceFilterForm(this, 'button.nav-link#sld-tab', '#sld-tab-pane');
});

$(document).on('click', '#sld-line-filter-reset', function () {
    const activeButton = document.querySelector('button.nav-link#sld-tab');
    if (!activeButton) {
        return;
    }
    loadWorkspaceContent(
        activeButton.dataset.url,
        activeButton.getAttribute('data-bs-target'),
        {},
        { scrollToSelector: '.sld-panel' }
    );
});

$(document).on('click', '.boq-line-quick-view', function () {
    const $button = $(this);
    const $row = $button.closest('tr');
    const $table = $button.closest('table[data-toggle="table"]');
    const index = Number($row.data('index'));

    if (!$table.length || Number.isNaN(index)) {
        return;
    }

    const isExpanded = $button.attr('data-expanded') === 'true';
    if (isExpanded) {
        $table.bootstrapTable('collapseRow', index);
    } else {
        $table.bootstrapTable('expandRow', index);
    }
});

$(document).on('expand-row.bs.table', '#boq-line-index-table', function (event, index, row, $detail) {
    const $table = $(this);
    $table.find('.boq-line-quick-view[data-expanded="true"]').each(function () {
        const $button = $(this);
        const rowIndex = Number($button.closest('tr').data('index'));
        if (!Number.isNaN(rowIndex) && rowIndex !== index) {
            $table.bootstrapTable('collapseRow', rowIndex);
        }
    });

    $table.find(`tr[data-index="${index}"] .boq-line-quick-view`)
        .attr('data-expanded', 'true')
        .text('Hide BOQ');
    loadBoqInlineDetail(this, index, row, $detail);
});

$(document).on('collapse-row.bs.table', '#boq-line-index-table', function (event, index) {
    $(this).find(`tr[data-index="${index}"] .boq-line-quick-view`)
        .attr('data-expanded', 'false')
        .text('Show BOQ');
});

$(document).ready(function () {
    initializeBootstrapTables(document);
    resetBootstrapTables(document);
});
