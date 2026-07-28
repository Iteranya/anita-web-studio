/**
 * MediaManager — Vanilla JS, zero dependencies.
 * Talks to /media/ endpoints, never touches PocketBase directly.
 */
(function () {
  'use strict';

  const ICONS = {
    jpg:'fa-image',jpeg:'fa-image',png:'fa-image',gif:'fa-image',webp:'fa-image',
    svg:'fa-image',avif:'fa-image',bmp:'fa-image',mp4:'fa-video',webm:'fa-video',
    mov:'fa-video',avi:'fa-video',mkv:'fa-video',mp3:'fa-music',wav:'fa-music',
    ogg:'fa-music',flac:'fa-music',aac:'fa-music',pdf:'fa-file-pdf',
    doc:'fa-file-word',docx:'fa-file-word',xls:'fa-file-excel',xlsx:'fa-file-excel',
    ppt:'fa-file-powerpoint',pptx:'fa-file-powerpoint',zip:'fa-file-archive',
    rar:'fa-file-archive','7z':'fa-file-archive',tar:'fa-file-archive',gz:'fa-file-archive',
    txt:'fa-file-alt',csv:'fa-file-csv'
  };
  const IMG = new Set(['jpg','jpeg','png','gif','webp','svg','avif','bmp']);

  function ext(filename) {
    if (!filename) return 'file';
    const p = filename.split('.');
    return p.length > 1 ? p.pop().toLowerCase() : 'file';
  }

  function icon(filename) { return ICONS[ext(filename)] || 'fa-file'; }
  function isImg(filename) { return IMG.has(ext(filename)); }

  // ─────────────────────────────────────
  //  QS helper — like $() but scoped
  // ─────────────────────────────────────
  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $$(sel, ctx) { return (ctx || document).querySelectorAll(sel); }

  const M = {
    files: [],
    page: 1,
    perPage: 25,
    total: 0,
    tab: 'all',
    search: '',
    timer: null,
    loading: false,
    target: null,       // currently selected file object
    uploading: false,

    // ── init ──
    init() {
      // search
      const si = $('#mm-search');
      if (si) si.addEventListener('input', () => {
        M.search = si.value;
        clearTimeout(M.timer);
        M.timer = setTimeout(() => { M.page = 1; M.load(); }, 350);
      });

      // tabs
      $$('[data-mm-tab]').forEach(b => b.addEventListener('click', () => {
        const t = b.dataset.mmTab;
        if (M.tab === t) return;
        M.tab = t; M.page = 1;
        $$('[data-mm-tab]').forEach(x => x.classList.remove('active'));
        b.classList.add('active');
        M.load();
      }));

      // upload trigger
      $('#mm-upload-btn')?.addEventListener('click', () => M.openUpload());
      $('#mm-single-btn')?.addEventListener('click', () => $('#mm-single-input')?.click());
      $('#mm-batch-btn')?.addEventListener('click', () => $('#mm-batch-input')?.click());
      // Drop zone — click to trigger single file input
      $('#mm-drop-zone')?.addEventListener('click', () => $('#mm-single-input')?.click());


      // file inputs
      $('#mm-single-input')?.addEventListener('change', e => {
        M._singleFile = e.target.files[0];
        if (M._singleFile && !$('#mm-upload-title').value)
          $('#mm-upload-title').value = M._singleFile.name.split('.')[0];
      });
      $('#mm-batch-input')?.addEventListener('change', e => {
        M._batchFiles = Array.from(e.target.files);
        if (M._batchFiles.length && !$('#mm-upload-title').value)
          $('#mm-upload-title').value = M._batchFiles.length === 1
            ? M._batchFiles[0].name.split('.')[0]
            : M._batchFiles.length + ' files';
      });

      // upload submit
      $('#mm-do-upload')?.addEventListener('click', () => M._doUpload());

      // details modal
      $('#mm-save-details')?.addEventListener('click', () => M._saveDetails());
      $('#mm-delete')?.addEventListener('click', () => M._delete());
      $('#mm-copy-link')?.addEventListener('click', () => M._copyLink());

      // close modals
      $$('[data-mm-close]').forEach(b => b.addEventListener('click', () => {
        $(b.dataset.mmClose)?.classList.add('hidden');
      }));

      // click-outside for modals
      document.addEventListener('click', e => {
        if (e.target.classList.contains('modal-overlay')) e.target.classList.add('hidden');
      });

      M.load();
    },

    // ── load ──
    async load(page) {
      if (page) M.page = page;
      M.loading = true;
      M._renderGrid();

      try {
        let u = `/media/?perPage=${M.perPage}&page=${M.page}&sort=-created`;

        // tab filter
        const tabMap = { images: 'image', video: 'video', audio: 'audio', document: 'document' };
        if (tabMap[M.tab]) u += `&category=${tabMap[M.tab]}`;

        // search
        if (M.search.trim()) u += `&search=${encodeURIComponent(M.search.trim())}`;

        const r = await fetch(u);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const data = await r.json();
        const items = Array.isArray(data) ? data : (data.files || data.items || []);

        M.files = items.map(item => ({
          id: item.id,
          filename: item.filename || '',
          original_name: item.original_name || '',
          friendly_name: item.friendly_name || '',
          description: item.description || '',
          format: item.format || ext(item.filename),
          size: item.size || 0,
          url: item.url || `/media/${item.filename}`,
          _icon: icon(item.filename),
          _img: isImg(item.filename),
          _display: item.friendly_name || item.original_name || (item.filename || '').split('.')[0] || '?',
          _sizeStr: item.size ? (item.size < 1048576 ? (item.size / 1024).toFixed(1) + ' KB' : (item.size / 1048576).toFixed(1) + ' MB') : '?',
        }));
        M.total = data.total || data.totalItems || items.length;
      } catch (e) {
        console.error('Media load failed:', e);
        M.files = [];
        M.total = 0;
      } finally {
        M.loading = false;
        M._renderGrid();
        M._renderPages();
      }
    },

    // ── upload ──
    openUpload() {
      M._singleFile = null;
      M._batchFiles = null;
      M.uploading = false;
      $('#mm-upload-title').value = '';
      $('#mm-upload-desc').value = '';
      $('#mm-single-input').value = '';
      $('#mm-batch-input').value = '';
      $('#mm-upload-modal')?.classList.remove('hidden');
    },

    async _doUpload() {
      const files = M._batchFiles && M._batchFiles.length ? M._batchFiles : (M._singleFile ? [M._singleFile] : null);
      if (!files || !files.length) return M._toast('error', 'Pilih file dulu~');

      M.uploading = true;
      $('#mm-do-upload').disabled = true;

      try {
        const fd = new FormData();
        files.forEach(f => fd.append('files', f));

        const r = await fetch('/media/', { method: 'POST', body: fd });
        if (!r.ok) throw new Error(await r.text().slice(0, 200));
        const result = await r.json();
        const uploaded = result.files || [];

        const title = $('#mm-upload-title').value.trim();
        const desc = $('#mm-upload-desc').value.trim();

        let ok = 0, fail = 0;
        for (const f of uploaded) {
          if (f.error) { fail++; continue; }
          // patch metadata
          if (f.id && (title || desc)) {
            try {
              await fetch(`/media/${f.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ friendly_name: title || undefined, description: desc || undefined }),
              });
            } catch {}
          }
          ok++;
        }

        $('#mm-upload-modal')?.classList.add('hidden');
        await M.load(1);
        M._toast('success', ok + ' file berhasil diupload' + (fail ? ', ' + fail + ' gagal' : '') + '~');

      } catch (e) {
        M._toast('error', 'Upload gagal: ' + e.message);
      } finally {
        M.uploading = false;
        $('#mm-do-upload').disabled = false;
      }
    },

    // ── details ──
    openDetails(file) {
      M.target = file;
      $('#mm-detail-title').value = file._display || '';
      $('#mm-detail-desc').value = file.description || '';
      $('#mm-detail-filename').textContent = file.filename || '?';
      $('#mm-detail-size').textContent = file._sizeStr || '?';
      $('#mm-detail-format').textContent = file.format || '?';
      const preview = $('#mm-detail-preview');
      if (preview) {
        if (file._img) { preview.src = file.url; preview.classList.remove('hidden'); }
        else { preview.classList.add('hidden'); }
      }
      $('#mm-details-modal')?.classList.remove('hidden');
    },

    async _saveDetails() {
      if (!M.target || !M.target.id) return;
      try {
        const r = await fetch(`/media/${M.target.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            friendly_name: $('#mm-detail-title').value.trim(),
            description: $('#mm-detail-desc').value.trim(),
          }),
        });
        if (!r.ok) throw new Error(await r.text().slice(0, 200));
        $('#mm-details-modal')?.classList.add('hidden');
        await M.load(M.page);
        M._toast('success', 'Metadata tersimpan~');
      } catch (e) {
        M._toast('error', 'Gagal: ' + e.message);
      }
    },

    async _delete() {
      if (!M.target) return;
      if (!confirm('Hapus permanen "' + (M.target._display || M.target.filename) + '"?')) return;
      try {
        const id = M.target.id || M.target.filename;
        await fetch(`/media/${encodeURIComponent(id)}`, { method: 'DELETE' });
        $('#mm-details-modal')?.classList.add('hidden');
        M.target = null;
        await M.load(M.page);
        M._toast('success', 'File dihapus~');
      } catch (e) {
        M._toast('error', 'Gagal hapus: ' + e.message);
      }
    },

    _copyLink() {
      if (!M.target || !M.target.url) return;
      navigator.clipboard.writeText(M.target.url)
        .then(() => M._toast('success', 'Link disalin!'))
        .catch(() => M._toast('error', 'Gagal menyalin'));
    },

    clearSearch() {
      const si = $('#mm-search');
      if (si) si.value = '';
      M.search = '';
      M.page = 1;
      M.load();
    },

    // ── pagination ──
    get totalPages() { return Math.max(1, Math.ceil(M.total / M.perPage)); },

    goTo(p) {
      if (p < 1 || p > M.totalPages || p === M.page) return;
      M.load(p);
    },

    // ── render ──
    _renderGrid() {
      const g = $('#mm-grid');
      if (!g) return;

      if (M.loading && !M.files.length) {
        g.innerHTML = '<div class="col-span-full text-center py-12 text-gray-400"><i class="fas fa-spinner fa-spin text-3xl"></i><p class="mt-2">Memuat...</p></div>';
      } else if (!M.files.length) {
        g.innerHTML = '<div class="col-span-full text-center py-12 text-gray-400"><i class="fas fa-folder-open text-3xl"></i><p class="mt-2">Kosong~</p></div>';
      } else {
        g.innerHTML = M.files.map(f =>
          `<div class="border rounded-lg overflow-hidden bg-white hover:shadow cursor-pointer group" data-mm-file="${f.id}">
            ${f._img
              ? `<img src="${f.url}" alt="${f._display}" class="w-full h-32 object-cover rounded-t" loading="lazy">`
              : `<div class="w-full h-32 flex items-center justify-center bg-gray-100 rounded-t"><i class="fas ${f._icon} text-4xl text-gray-400"></i></div>`}
            <div class="p-2">
              <p class="text-xs truncate font-medium" title="${f._display}">${f._display}</p>
              <p class="text-xs text-gray-400">${f.format || '?'} · ${f._sizeStr}</p>
            </div>
          </div>`
        ).join('');

        // click to open details
        $$('[data-mm-file]', g).forEach(el => {
          el.addEventListener('click', () => {
            const file = M.files.find(f => f.id === el.dataset.mmFile);
            if (file) M.openDetails(file);
          });
        });
      }
    },

    _renderPages() {
      const c = $('#mm-pagination');
      if (!c) return;
      const tp = M.totalPages;
      if (tp <= 1) { c.innerHTML = ''; return; }

      const range = [];
      const cv = 7;
      let s = Math.max(1, M.page - Math.floor(cv / 2));
      let e = Math.min(tp, s + cv - 1);
      if (e - s < cv - 1) s = Math.max(1, e - cv + 1);
      for (let i = s; i <= e; i++) range.push(i);

      let h = `<button data-mm-page="1" ${M.page===1?'disabled':''} class="px-2 py-1 text-xs border rounded">««</button>`;
      h += `<button data-mm-page="${M.page-1}" ${M.page===1?'disabled':''} class="px-2 py-1 text-xs border rounded">«</button>`;
      for (const p of range) {
        h += `<button data-mm-page="${p}" class="px-3 py-1 text-xs border rounded ${p===M.page?'bg-cyan-500 text-white':''}">${p}</button>`;
      }
      h += `<button data-mm-page="${M.page+1}" ${M.page===tp?'disabled':''} class="px-2 py-1 text-xs border rounded">»</button>`;
      h += `<button data-mm-page="${tp}" ${M.page===tp?'disabled':''} class="px-2 py-1 text-xs border rounded">»»</button>`;

      c.innerHTML = h;
      $$('[data-mm-page]', c).forEach(b => b.addEventListener('click', () => M.goTo(+b.dataset.mmPage)));
    },

    _toast(type, msg) {
      // hook your notification system here, or use a simple DOM toast
      const ev = new CustomEvent('anita:toast', { detail: { type, message: msg } });
      window.dispatchEvent(ev);
      if (type === 'error') console.error(msg); else console.log(msg);
    },
  };
  document.addEventListener('DOMContentLoaded', () => M.init());
  window.MediaManager = M;
})();