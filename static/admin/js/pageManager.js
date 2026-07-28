/**
 * PageManager — Vanilla JS, zero dependencies.
 * Lists pages, creates new ones, deletes. Editing links to the Aina editor.
 */
(function () {
  'use strict';

  const Q = (s, c) => (c || document).querySelector(s);
  const QA = (s, c) => (c || document).querySelectorAll(s);

  const P = {
    pages: [],
    filter: 'all',   // 'all' | 'markdown' | 'html'

    init() {
      // New page button
      Q('#pm-new-page')?.addEventListener('click', () => P._openCreate());
      // Create form submit
      Q('#pm-create-form')?.addEventListener('submit', e => {
        e.preventDefault();
        P._doCreate();
      });
      // Cancel create
      Q('#pm-cancel-create')?.addEventListener('click', () => {
        Q('#pm-create-modal')?.classList.add('hidden');
      });
      // Filter tabs
      QA('[data-pm-filter]').forEach(b => b.addEventListener('click', () => {
        P.filter = b.dataset.pmFilter;
        QA('[data-pm-filter]').forEach(x => x.classList.remove('active'));
        b.classList.add('active');
        P.load();
      }));
      // Delete
      Q('#pm-delete')?.addEventListener('click', () => P._delete());
      // Close modals
      QA('[data-pm-close]').forEach(b => b.addEventListener('click', () => {
        Q(b.dataset.pmClose)?.classList.add('hidden');
      }));

      P.load();
    },

    async load() {
      try {
        let url = '/page/list';
        if (P.filter === 'markdown') url = '/page/list/markdown';
        else if (P.filter === 'html') url = '/page/list/html';

        const r = await fetch(url);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        P.pages = await r.json();
        P._render();
      } catch (e) {
        console.error('PageManager load failed:', e);
        P.pages = [];
        P._render();
      }
    },

    _openCreate() {
      Q('#pm-create-slug').value = '';
      Q('#pm-create-title').value = '';
      Q('#pm-create-type').value = 'markdown';
      Q('#pm-create-modal')?.classList.remove('hidden');
    },

    async _doCreate() {
      const title = Q('#pm-create-title').value.trim();
      const slug  = Q('#pm-create-slug').value.trim() || title.toLowerCase().replace(/\s+/g, '-').replace(/[^\w-]/g, '');
      const type  = Q('#pm-create-type').value;

      if (!title) return;

      try {
        const r = await fetch('/page/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, slug, type }),
        });
        if (!r.ok) {
          const err = await r.text().catch(() => 'Unknown');
          throw new Error(err.slice(0, 200));
        }

        Q('#pm-create-modal')?.classList.add('hidden');
        await P.load();

        // Redirect to editor
        if (type === 'html') {
          window.location.href = '/admin/page?slug=' + encodeURIComponent(slug);
        } else {
          window.location.href = '/admin/page?slug=' + encodeURIComponent(slug);
        }
      } catch (e) {
        alert('Gagal membuat: ' + e.message);
      }
    },

    _confirmDelete(page) {
      P._target = page;
      const el = Q('#pm-delete-title');
        if (el) el.textContent = page.title || page.slug;
      Q('#pm-delete-modal')?.classList.remove('hidden');
    },

    async _delete() {
      if (!P._target) return;
      try {
        await fetch('/page/' + encodeURIComponent(P._target.slug), { method: 'DELETE' });
        Q('#pm-delete-modal')?.classList.add('hidden');
        P._target = null;
        await P.load();
      } catch (e) {
        alert('Gagal hapus: ' + e.message);
      }
    },

    _render() {
      const tbody = Q('#pm-table-body');
      if (!tbody) return;

      if (!P.pages.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="p-4 text-center text-gray-400">Belum ada halaman~</td></tr>';
        return;
      }

      tbody.innerHTML = P.pages.map(p => `
        <tr class="border-b hover:bg-gray-50">
          <td class="p-3 pr-0 w-4">
            <input type="checkbox" class="pm-checkbox" data-slug="${p.slug}">
          </td>
          <td class="p-3 font-medium">
            <a href="/admin/page?slug=${encodeURIComponent(p.slug)}" class="text-cyan-600 hover:underline">
              ${p.title || '(tanpa judul)'}
            </a>
            <div class="text-xs text-gray-400">/${p.slug}</div>
          </td>
          <td class="p-3 text-xs">
            <span class="px-2 py-0.5 rounded ${p.type === 'html' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'}">
              ${p.type || 'markdown'}
            </span>
          </td>
          <td class="p-3 text-xs text-gray-400">${p.author || '?'}</td>
          <td class="p-3 text-right">
            <a href="/editor/raw/${encodeURIComponent(p.slug)}" class="text-xs text-gray-500 hover:text-cyan-600 mr-3">
              <i class="fas fa-edit"></i> Edit
            </a>
            <button data-pm-delete="${p.slug}" class="text-xs text-red-400 hover:text-red-600">
              <i class="fas fa-trash"></i>
            </button>
          </td>
        </tr>
      `).join('');

      // Bind delete buttons
      QA('[data-pm-delete]', tbody).forEach(b => {
        b.addEventListener('click', () => {
          const slug = b.dataset.pmDelete;
          const page = P.pages.find(p => p.slug === slug);
          if (page) P._confirmDelete(page);
        });
      });
    },

    _toast(type, msg) {
      window.dispatchEvent(new CustomEvent('anita:toast', { detail: { type, message: msg } }));
    }
  };

  document.addEventListener('DOMContentLoaded', () => P.init());
  window.PageManager = P;
})();
