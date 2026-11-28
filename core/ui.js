/**
 * Shared UI helpers: escaping, theme CSS injection, SVG icons, sortable tables,
 * contextual dossier navigation bars, toast notifications, and zoomable image lightbox.
 */

export function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function applyTheme(themeObj = {}) {
  const root = document.documentElement;
  const defaults = {
    '--bg-primary': '#0c0e12',
    '--bg-secondary': '#11141a',
    '--bg-surface': '#161a22',
    '--bg-elevated': '#1e2430',
    '--bg-hover': '#252c3b',
    '--border-subtle': 'rgba(255, 255, 255, 0.08)',
    '--border-default': 'rgba(255, 255, 255, 0.13)',
    '--border-strong': 'rgba(255, 255, 255, 0.22)',
    '--accent': '#4ea89b',
    '--accent-rgb': '78, 168, 155',
    '--accent-secondary': '#7b9cc4',
    '--accent-secondary-rgb': '123, 156, 196',
    '--accent-warn': '#d49a45',
    '--accent-warn-rgb': '212, 154, 69',
    '--accent-danger': '#d46a6a',
    '--accent-danger-rgb': '212, 106, 106',
    '--accent-purple': '#a78bca',
    '--text-primary': '#eceff4',
    '--text-secondary': '#b8c0cc',
    '--text-muted': '#7c8798'
  };
  const merged = { ...defaults, ...themeObj };
  for (const [k, v] of Object.entries(merged)) {
    root.style.setProperty(k, v);
  }
}

const ICONS = {
  home: '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5.5v-6.5h-5V21H4a1 1 0 0 1-1-1z"/>',
  layout: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
  compass: '<circle cx="12" cy="12" r="9"/><polygon points="15.5 8.5 13.8 13.8 8.5 15.5 10.2 10.2 15.5 8.5"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
  flask: '<path d="M10 2v6l-5 9.5A2 2 0 0 0 6.75 20.5h10.5a2 2 0 0 0 1.75-3L14 8V2"/><path d="M8.5 2h7"/><path d="M7 14h10"/>',
  skull: '<circle cx="12" cy="10" r="7"/><path d="M9 17v3h6v-3"/><circle cx="9.5" cy="10.5" r="1"/><circle cx="14.5" cy="10.5" r="1"/>',
  trophy: '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
  sparkles: '<path d="m12 3 1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9Z"/><path d="M5 3v4"/><path d="M3 5h4"/><path d="M19 17v4"/><path d="M17 19h4"/>',
  'book-open': '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
  'arrow-left': '<path d="M19 12H5"/><path d="m12 19-7-7 7-7"/>',
  'arrow-right': '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
  'chevron-left': '<path d="m15 18-6-6 6-6"/>',
  'chevron-right': '<path d="m9 18 6-6-6-6"/>',
  search: '<circle cx="11" cy="11" r="7.5"/><path d="m20 20-3.5-3.5"/>',
  menu: '<path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h16"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  refresh: '<path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  'filter-x': '<path d="M13.013 3H2l8 9.46V19l4 2v-8.54l.9-1.055"/><path d="m22 3-5 5"/><path d="m17 3 5 5"/>',
  'external-link': '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
  gamepad: '<line x1="6" y1="11" x2="10" y2="11"/><line x1="8" y1="9" x2="8" y2="13"/><line x1="15" y1="12" x2="15.01" y2="12"/><line x1="18" y1="10" x2="18.01" y2="10"/><path d="M17.32 5H6.68a4 4 0 0 0-3.978 3.59c-.006.052-.01.101-.017.152C2.604 9.416 2 14.456 2 16a3 3 0 0 0 3 3c1 0 1.5-.5 2-1l1.414-1.414A2 2 0 0 1 9.828 16h4.344a2 2 0 0 1 1.414.586L17 18c.5.5 1 1 2 1a3 3 0 0 0 3-3c0-1.545-.604-6.584-.685-7.258-.007-.05-.011-.1-.017-.151A4 4 0 0 0 17.32 5z"/>',
  layers: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  sliders: '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>'
};

export function icon(name, size = 16) {
  const body = ICONS[name] || ICONS.layers;
  return `<svg class="ui-icon" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
}

export function renderDossierNavBar({ router, listRoute, listLabel, rightHtml = '' }) {
  const prev = router?.getPreviousEntry ? router.getPreviousEntry() : null;
  const current = router?.currentHash ? router.currentHash() : '';
  const hasDistinctPrev = Boolean(prev && prev.hash && prev.hash !== current);

  let leftHtml = '';
  if (hasDistinctPrev) {
    const prevLabel = prev.label ? `Back to ${prev.label}` : 'Back to Previous Page';
    leftHtml = `
      <button type="button" class="btn btn-sm dossier-back-btn" data-dossier-back="1">
        ${icon('arrow-left', 14)}
        <span>${escapeHtml(prevLabel)}</span>
      </button>
      ${prev.hash !== listRoute ? `<a class="btn btn-ghost btn-sm" href="${escapeHtml(listRoute)}">${escapeHtml(listLabel)}</a>` : ''}
    `;
  } else {
    leftHtml = `
      <a class="btn btn-sm" href="${escapeHtml(listRoute)}">
        ${icon('arrow-left', 14)}
        <span>${escapeHtml(listLabel)}</span>
      </a>
    `;
  }

  return `
    <div class="dossier-nav-bar">
      <div class="dossier-nav-left">${leftHtml}</div>
      ${rightHtml ? `<div class="dossier-nav-right">${rightHtml}</div>` : ''}
    </div>
  `;
}

export function wireDossierNavBar(container, router) {
  container.querySelector('[data-dossier-back]')?.addEventListener('click', () => {
    router?.back();
  });
}

export function showToast(message, tone = 'info') {
  let host = document.getElementById('toast-host');
  if (!host) {
    host = document.createElement('div');
    host.id = 'toast-host';
    host.className = 'toast-host';
    document.body.appendChild(host);
  }
  const el = document.createElement('div');
  el.className = `toast toast-${tone}`;
  el.textContent = message;
  host.appendChild(el);
  setTimeout(() => {
    el.classList.add('toast-out');
    setTimeout(() => el.remove(), 250);
  }, 3000);
}

export function openLightbox({ src, fallbackSrc, title = '', subtitle = '' }) {
  closeLightbox();
  const overlay = document.createElement('div');
  overlay.id = 'wiki-lightbox';
  overlay.className = 'lightbox-overlay';
  overlay.innerHTML = `
    <div class="lightbox-card" role="dialog" aria-modal="true">
      <div class="lightbox-head">
        <div>
          <strong>${escapeHtml(title)}</strong>
          ${subtitle ? `<div class="muted small">${escapeHtml(subtitle)}</div>` : ''}
        </div>
        <button class="btn btn-ghost btn-sm" id="lb-close" aria-label="Close">${icon('x', 15)}</button>
      </div>
      <div class="lightbox-body">
        <img id="lb-img" referrerpolicy="no-referrer" src="${escapeHtml(src || fallbackSrc || '')}" alt="${escapeHtml(title)}" />
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
  const img = overlay.querySelector('#lb-img');
  if (fallbackSrc && src !== fallbackSrc) {
    img.addEventListener('error', () => {
      if (img.src !== fallbackSrc) img.src = fallbackSrc;
    }, { once: true });
  }
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay || e.target.closest('#lb-close')) closeLightbox();
  });
  const esc = (e) => {
    if (e.key === 'Escape') {
      closeLightbox();
      document.removeEventListener('keydown', esc);
    }
  };
  document.addEventListener('keydown', esc);
}

export function closeLightbox() {
  const existing = document.getElementById('wiki-lightbox');
  if (existing) existing.remove();
}

export function formatNum(n) {
  if (n === null || n === undefined || n === '') return '—';
  const num = Number(n);
  return Number.isFinite(num) ? num.toLocaleString() : String(n);
}

/**
 * Attaches sortable header behavior to a table container.
 * columns: [{ key, label, numeric?, render(row) }]
 */
export function renderSortableTable({
  container,
  rows,
  columns,
  initialSortKey = null,
  initialSortDir = 'asc',
  onRowClick = null,
  onSortChange = null,
  emptyMessage = 'No matching entries found.'
}) {
  let sortKey = initialSortKey;
  let sortDir = initialSortDir;

  function draw() {
    const sorted = [...rows];
    if (sortKey) {
      const col = columns.find((c) => c.key === sortKey);
      sorted.sort((a, b) => {
        const va = col?.sortValue ? col.sortValue(a) : a[sortKey];
        const vb = col?.sortValue ? col.sortValue(b) : b[sortKey];
        let cmp = 0;
        if (col?.numeric) {
          cmp = (Number(va) || 0) - (Number(vb) || 0);
        } else {
          cmp = String(va ?? '').localeCompare(String(vb ?? ''), undefined, { numeric: true });
        }
        return sortDir === 'asc' ? cmp : -cmp;
      });
    }

    if (!sorted.length) {
      container.innerHTML = `<div class="empty-state">${escapeHtml(emptyMessage)}</div>`;
      return;
    }

    const headHtml = columns
      .map((c) => {
        const active = sortKey === c.key;
        const arrow = active ? (sortDir === 'asc' ? ' ▲' : ' ▼') : '';
        return `<th class="${c.sortable !== false ? 'sortable' : ''} ${active ? 'sorted' : ''}" data-sort-key="${escapeHtml(c.key)}">${escapeHtml(c.label)}${arrow}</th>`;
      })
      .join('');

    const bodyHtml = sorted
      .map((row, idx) => {
        const tds = columns
          .map((c) => `<td data-label="${escapeHtml(c.label)}">${c.render ? c.render(row) : escapeHtml(row[c.key])}</td>`)
          .join('');
        return `<tr data-row-idx="${idx}" class="${onRowClick ? 'clickable-row' : ''}">${tds}</tr>`;
      })
      .join('');

    container.innerHTML = `
      <div class="table-wrap">
        <table class="wiki-table">
          <thead><tr>${headHtml}</tr></thead>
          <tbody>${bodyHtml}</tbody>
        </table>
      </div>
    `;

    container.querySelectorAll('th.sortable').forEach((th) => {
      th.addEventListener('click', () => {
        const k = th.dataset.sortKey;
        const col = columns.find((c) => c.key === k);
        if (!col || col.sortable === false) return;
        if (sortKey === k) {
          sortDir = sortDir === 'asc' ? 'desc' : 'asc';
        } else {
          sortKey = k;
          sortDir = 'asc';
        }
        if (typeof onSortChange === 'function') {
          onSortChange(sortKey, sortDir);
        }
        draw();
      });
    });

    if (onRowClick) {
      container.querySelectorAll('tbody tr').forEach((tr) => {
        tr.addEventListener('click', (e) => {
          if (e.target.closest('a, button, input, label')) return;
          const idx = Number(tr.dataset.rowIdx);
          onRowClick(sorted[idx]);
        });
      });
    }
  }

  draw();
}
