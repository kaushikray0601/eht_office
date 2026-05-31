(function () {
    'use strict';

    /* ── Scroll progress bar ─────────────────────────────── */
    const progressBar = document.querySelector('.dg-progress-bar');
    function updateProgress() {
        if (!progressBar) return;
        const max = document.documentElement.scrollHeight - window.innerHeight;
        const pct = max > 0 ? (window.scrollY / max) * 100 : 0;
        progressBar.style.width = pct + '%';
    }

    /* ── Back-to-top ─────────────────────────────────────── */
    const backTop = document.querySelector('.dg-back-top');
    function updateBackTop() {
        if (!backTop) return;
        if (window.scrollY > 400) backTop.classList.add('visible');
        else                       backTop.classList.remove('visible');
    }

    /* ── Active TOC link ─────────────────────────────────── */
    const tocLinks = Array.from(document.querySelectorAll('.dg-toc-link'));
    const headings = Array.from(document.querySelectorAll('.dg-article h1, .dg-article h2, .dg-article h3'));

    function updateToc() {
        if (!headings.length || !tocLinks.length) return;
        const navH = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--nav-h')) || 58;
        const top = window.scrollY + navH + 20;
        let active = null;
        for (const h of headings) {
            if (h.offsetTop <= top) active = h;
        }
        tocLinks.forEach(l => l.classList.remove('active'));
        if (active && active.id) {
            const link = tocLinks.find(l => l.getAttribute('href') === '#' + active.id);
            if (link) link.classList.add('active');
        }
    }

    window.addEventListener('scroll', () => {
        updateProgress();
        updateBackTop();
        updateToc();
    }, { passive: true });

    updateProgress();
    updateBackTop();
    updateToc();

    /* ── Formula cards (click to expand) ────────────────── */
    document.querySelectorAll('.dg-formula-card').forEach(card => {
        card.addEventListener('click', () => {
            card.classList.toggle('expanded');
        });
        card.setAttribute('tabindex', '0');
        card.addEventListener('keydown', e => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                card.classList.toggle('expanded');
            }
        });
    });

    /* ── Diagnostics flip cards ──────────────────────────── */
    document.querySelectorAll('.dg-diag-card').forEach(card => {
        card.addEventListener('click', () => card.classList.toggle('flipped'));
        card.setAttribute('tabindex', '0');
        card.addEventListener('keydown', e => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                card.classList.toggle('flipped');
            }
        });
    });

    /* ── Print ───────────────────────────────────────────── */
    document.querySelectorAll('[data-dg-print]').forEach(btn => {
        btn.addEventListener('click', () => window.print());
    });

    /* ── Search ──────────────────────────────────────────── */
    const searchForm   = document.querySelector('[data-dg-search]');
    const searchInput  = document.getElementById('dg-search-input');
    const clearBtn     = document.querySelector('[data-dg-clear]');
    const resultsEl    = document.querySelector('[data-dg-results]');
    const statusEl     = document.querySelector('[data-dg-status]');
    const searchShell  = document.querySelector('.dg-shell');

    if (searchForm && searchInput && resultsEl && statusEl) {
        const targets = Array.from(
            document.querySelectorAll('.dg-shell h1, .dg-shell h2, .dg-shell h3, .dg-shell p, .dg-shell li, .dg-shell td')
        ).filter(n => !n.closest('.dg-search-section'))
          .map(n => ({ node: n, text: n.textContent.replace(/\s+/g, ' ').trim() }))
          .filter(i => i.text.length > 0);

        function snippet(text, term) {
            const idx = text.toLowerCase().indexOf(term.toLowerCase());
            if (idx < 0) return text.slice(0, 120);
            const s = Math.max(0, idx - 40);
            const e = Math.min(text.length, idx + term.length + 80);
            return (s > 0 ? '…' : '') + text.slice(s, e) + (e < text.length ? '…' : '');
        }

        function nearestHeading(node) {
            let cur = node;
            while (cur && cur !== searchShell) {
                if (/^H[1-4]$/.test(cur.tagName) && cur.id) return cur;
                let prev = cur.previousElementSibling;
                while (prev) {
                    if (/^H[1-4]$/.test(prev.tagName) && prev.id) return prev;
                    prev = prev.previousElementSibling;
                }
                cur = cur.parentElement;
            }
            return null;
        }

        function clearResults() {
            resultsEl.replaceChildren();
            statusEl.textContent = 'Search across formulas, workflow steps, diagnostics, and the full manual.';
        }

        function runSearch(query) {
            query = query.trim();
            if (!query) { clearResults(); return; }
            if (query.length < 3) {
                resultsEl.replaceChildren();
                statusEl.textContent = 'Type at least 3 characters to search.';
                return;
            }
            const low = query.toLowerCase();
            const matches = targets.filter(i => i.text.toLowerCase().includes(low));
            const visible = matches.slice(0, 8);

            resultsEl.replaceChildren(
                ...visible.map(item => {
                    const h = nearestHeading(item.node);
                    const a = document.createElement('a');
                    a.href = h && h.id ? '#' + h.id : '#top';
                    const strong = document.createElement('strong');
                    strong.textContent = h ? h.textContent : 'Guide section';
                    const span = document.createElement('span');
                    span.textContent = snippet(item.text, query);
                    a.append(strong, span);
                    return a;
                })
            );

            if (!matches.length) {
                const p = document.createElement('p');
                p.style.cssText = 'font-size:13px;color:var(--muted);padding:8px 0;';
                p.textContent = 'No results found for "' + query + '".';
                resultsEl.replaceChildren(p);
            }

            const extra = matches.length > visible.length ? ` Showing first ${visible.length}.` : '';
            statusEl.textContent = `${matches.length} result${matches.length === 1 ? '' : 's'} for "${query}".${extra}`;
        }

        searchForm.addEventListener('submit', e => { e.preventDefault(); runSearch(searchInput.value); });
        searchInput.addEventListener('input', () => {
            if (!searchInput.value.trim()) clearResults();
            else { resultsEl.replaceChildren(); statusEl.textContent = 'Press Enter or Search to run.'; }
        });
        if (clearBtn) clearBtn.addEventListener('click', () => { searchInput.value = ''; clearResults(); searchInput.focus(); });
    }

    /* ── Manual reader: font size controls ──────────────── */
    const articleEl = document.getElementById('dg-article');
    const sectionLabel = document.getElementById('dg-reader-active-section');
    let articleFontSize = 15;

    document.querySelectorAll('[data-dg-font]').forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.getAttribute('data-dg-font');
            if (action === '+' && articleFontSize < 22) articleFontSize += 1;
            else if (action === '-' && articleFontSize > 12) articleFontSize -= 1;
            else if (action === '0') articleFontSize = 15;
            if (articleEl) articleEl.style.fontSize = articleFontSize + 'px';
            document.querySelectorAll('[data-dg-font]').forEach(b => b.classList.remove('active'));
            if (action === '0' || articleFontSize === 15) {
                document.querySelector('[data-dg-font="0"]')?.classList.add('active');
            }
        });
    });

    /* ── Reader active-section label tracking ────────────── */
    if (sectionLabel && articleEl) {
        const articleHeadings = Array.from(articleEl.querySelectorAll('h1, h2, h3'));
        function updateSectionLabel() {
            const navH = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--nav-h')) || 58;
            const offset = window.scrollY + navH + 60;
            let active = null;
            for (const h of articleHeadings) {
                if (h.offsetTop <= offset) active = h;
            }
            if (active) {
                sectionLabel.innerHTML = '<i class="bi bi-book" style="margin-right:5px; opacity:.6;"></i>' +
                    active.textContent.replace(/^#+\s*/, '');
            }
        }
        window.addEventListener('scroll', updateSectionLabel, { passive: true });
    }

    /* ── Smooth-reveal on scroll (Intersection Observer) ── */
    const revealEls = document.querySelectorAll('.dg-fact, .dg-formula-card, .dg-tech-card, .dg-diag-card');
    if ('IntersectionObserver' in window) {
        const io = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12 });

        revealEls.forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'opacity .45s ease, transform .45s ease';
            io.observe(el);
        });
    }

}());
