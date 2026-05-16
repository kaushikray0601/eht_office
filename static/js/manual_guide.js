(function () {
    const printButtons = document.querySelectorAll('[data-print-guide]');
    const form = document.querySelector('[data-guide-search]');
    const input = document.getElementById('manual-search-input');
    const clearButton = document.querySelector('[data-clear-search]');
    const results = document.querySelector('[data-search-results]');
    const status = document.querySelector('[data-search-status]');
    const searchableRoot = document.querySelector('.manual-shell');

    printButtons.forEach((button) => {
        button.addEventListener('click', () => window.print());
    });

    if (!form || !input || !results || !status || !searchableRoot) {
        return;
    }

    const targets = Array.from(searchableRoot.querySelectorAll(
        'h1, h2, h3, p, li, td, th'
    )).filter((node) => !node.closest('.manual-utility-panel')).map((node) => ({
        node,
        text: node.textContent.replace(/\s+/g, ' ').trim(),
    })).filter((item) => item.text.length > 0);

    function snippet(text, term) {
        const index = text.toLowerCase().indexOf(term.toLowerCase());
        if (index < 0) {
            return text.slice(0, 120);
        }
        const start = Math.max(0, index - 38);
        const end = Math.min(text.length, index + term.length + 82);
        return `${start > 0 ? '...' : ''}${text.slice(start, end)}${end < text.length ? '...' : ''}`;
    }

    function closestHeading(node) {
        let current = node;
        while (current && current !== searchableRoot) {
            if (/^H[1-3]$/.test(current.tagName) && current.id) {
                return current;
            }
            let previous = current.previousElementSibling;
            while (previous) {
                if (/^H[1-3]$/.test(previous.tagName) && previous.id) {
                    return previous;
                }
                previous = previous.previousElementSibling;
            }
            current = current.parentElement;
        }
        return null;
    }

    function clearResults() {
        results.replaceChildren();
        status.textContent = 'Search covers guide cards, flow sections, and the rendered manual.';
    }

    function buildResult(item, term) {
        const heading = closestHeading(item.node);
        const link = document.createElement('a');
        const title = document.createElement('strong');
        const excerpt = document.createElement('span');

        link.href = heading && heading.id ? `#${heading.id}` : '#top';
        title.textContent = heading && heading.textContent ? heading.textContent : 'Guide section';
        excerpt.textContent = snippet(item.text, term);
        link.append(title, excerpt);
        link.addEventListener('click', () => {
            item.node.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
        return link;
    }

    function runSearch(term) {
        const query = term.trim();

        if (!query) {
            clearResults();
            return;
        }

        if (query.length < 3) {
            results.replaceChildren();
            status.textContent = 'Type at least 3 characters, then press Search.';
            return;
        }

        const lowered = query.toLowerCase();
        const matches = targets.filter((item) => item.text.toLowerCase().includes(lowered));
        const visibleMatches = matches.slice(0, 8);
        results.replaceChildren(...visibleMatches.map((item) => buildResult(item, query)));

        if (!matches.length) {
            const empty = document.createElement('p');
            empty.className = 'manual-search-empty';
            empty.textContent = 'No matching guide content found.';
            results.replaceChildren(empty);
        }

        const suffix = matches.length > visibleMatches.length
            ? ` Showing first ${visibleMatches.length}.`
            : '';
        status.textContent = `${matches.length} result${matches.length === 1 ? '' : 's'} for "${query}".${suffix}`;
    }

    form.addEventListener('submit', (event) => {
        event.preventDefault();
        runSearch(input.value);
    });

    input.addEventListener('input', () => {
        const query = input.value.trim();
        if (!query) {
            clearResults();
            return;
        }
        if (query.length < 3) {
            results.replaceChildren();
            status.textContent = 'Type at least 3 characters, then press Search.';
            return;
        }
        results.replaceChildren();
        status.textContent = 'Press Search or Enter to run the manual search.';
    });

    clearButton.addEventListener('click', () => {
        input.value = '';
        clearResults();
        input.focus();
    });
}());
