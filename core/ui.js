/**
 * Shared UI helpers: escaping, theme CSS injection, sortable tables, badges,
 * toast notifications, and zoomable image lightbox.
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
    '--bg-primary': '#070b10',
    '--bg-secondary': '#0b1119',
    '--bg-surface': '#0f1722',
    '--bg-elevated': '#15202e',
    '--border-subtle': 'rgba(56, 189, 248, 0.16)',
    '--border-strong': 'rgba(0, 229, 163, 0.42)',
    '--accent': '#00e5a3',
    '--accent-rgb': '0, 229, 163',
    '--accent-secondary': '#38bdf8',
    '--accent-warn': '#f59e0b',
    '--accent-danger': '#ef4444',
    '--text-primary': '#e6f1f8',
    '--text-muted': '#8aa0b8'
  };
  const merged = { ...defaults, ...themeObj };
  for (const [k, v] of Object.entries(merged)) {
    root.style.setProperty(k, v);
  }
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
        <button class="btn btn-ghost btn-sm" id="lb-close" aria-label="Close">✕</button>
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
    if (e.target === overlay || e.target.id === 'lb-close') closeLightbox();
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
