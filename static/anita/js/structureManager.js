/**
 * StructureManager — Vanilla JS, zero dependencies.
 * Manages site structure: groups pages by category, drag-and-drop reordering.
 * Talks to /page/ endpoints. No Alpine. No $api.
 */
(function () {
  'use strict';

  const Q = (s, c) => (c || document).querySelector(s);
  const QA = (s, c) => (c || document).querySelectorAll(s);

  const S = {
    pages: [],
    roles: [],
    tree: {},
    openGroups: ['uncategorized'],
    isCreatingGroup: false,
    newGroupName: '',

    // Drag state
    _dragSlug: null,
    _dragGroup: null,

    async init() {
      // Delegated events
      document.addEventListener('click', e => {
        const btn = e.target.closest('[data-sm-action]');
        if (!btn) return;
        const action = btn.dataset.smAction;

        // --- ADD THIS BLOCK ---
        if (action === 'create-new-group') {
          S.isCreatingGroup = true;
          S._render();
          setTimeout(() => Q('#sm-new-group-input')?.focus(), 50);
        }
        // ----------------------

        if (action === 'toggle-group') {
          const group = btn.dataset.smGroup;
          S.toggleGroup(group);
        }
        if (action === 'confirm-new-group') {
          S.addNewGroup();
        }
        if (action === 'cancel-new-group') {
          S.isCreatingGroup = false;
          S.newGroupName = '';
          S._render();
        }
        if (action === 'toggle-label') {
          e.preventDefault();
          const slug = btn.dataset.smSlug;
          const label = btn.dataset.smLabel;
          S.togglePageLabel(slug, label);
        }
      });

      // New group input Enter key
      document.addEventListener('keydown', e => {
        if (e.key === 'Enter' && S.isCreatingGroup) {
          const input = Q('#sm-new-group-input');
          if (input === document.activeElement) {
            S.newGroupName = input.value;
            S.addNewGroup();
          }
        }
        if (e.key === 'Escape' && S.isCreatingGroup) {
          S.isCreatingGroup = false;
          S.newGroupName = '';
          S._render();
        }
      });

      await S.load();
    },

    // ═══════════════════════════════════
    //  DATA
    // ═══════════════════════════════════

    async load() {
      try {
        const [pagesRes, rolesRes] = await Promise.all([
          fetch('/page/list'),
          fetch('/users/roles').catch(() => null),
        ]);

        if (!pagesRes.ok) throw new Error('HTTP ' + pagesRes.status);
        S.pages = await pagesRes.json();

        if (rolesRes && rolesRes.ok) {
          S.roles = await rolesRes.json();
        }

        S.buildTree();
        S._render();
      } catch (e) {
        console.error('StructureManager load failed:', e);
        S.pages = [];
        S.tree = {};
        S._render();
      }
    },

    buildTree() {
      const currentKeys = Object.keys(S.tree);
      const tree = { uncategorized: [] };

      // Preserve empty user-created groups
      currentKeys.forEach(key => {
        if (key !== 'uncategorized') tree[key] = [];
      });

      // Distribute pages by main: label
      S.pages.forEach(page => {
        const labels = page.labels || [];
        const mainLabel = labels.find(l => l.startsWith('main:'));
        const groupName = mainLabel ? mainLabel.split(':')[1] : 'uncategorized';

        if (!tree[groupName]) tree[groupName] = [];
        tree[groupName].push(page);
      });

      // Sort keys alphabetically, uncategorized always last
      const sortedKeys = Object.keys(tree).sort((a, b) => {
        if (a === 'uncategorized') return 1;
        if (b === 'uncategorized') return -1;
        return a.localeCompare(b);
      });

      const sortedTree = {};
      sortedKeys.forEach(key => {
        sortedTree[key] = tree[key];
        // Auto-open groups that have pages
        if (!S.openGroups.includes(key) && tree[key].length > 0) {
          S.openGroups.push(key);
        }
      });

      S.tree = sortedTree;
    },

    // ═══════════════════════════════════
    //  PAGE ACTIONS & TOGGLES
    // ═══════════════════════════════════

    async togglePageLabel(slug, targetLabel) {
      // Find the page locally
      let page = null;
      for (const group in S.tree) {
        page = S.tree[group].find(p => p.slug === slug);
        if (page) break;
      }
      if (!page) return;

      const labels = page.labels || [];
      const hasLabel = labels.includes(targetLabel);

      // Toggle logic
      const newLabels = hasLabel
        ? labels.filter(l => l !== targetLabel)
        : [...labels, targetLabel];

      page.labels = newLabels;

      // Re-render optimistically
      S._render();

      // Save to server
      try {
        const r = await fetch('/page/' + encodeURIComponent(slug), {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(page),
        });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        S._toast('success', 'Status halaman diperbarui');
      } catch (e) {
        console.error('Toggle failed:', e);
        S._toast('error', 'Gagal memperbarui, memuat ulang...');
        await S.load();
      }
    },

    // ═══════════════════════════════════
    //  GROUP ACTIONS
    // ═══════════════════════════════════

    toggleGroup(groupName) {
      if (S.openGroups.includes(groupName)) {
        S.openGroups = S.openGroups.filter(g => g !== groupName);
      } else {
        S.openGroups.push(groupName);
      }
      S._render();
    },

    addNewGroup() {
      const name = (S.newGroupName || '').trim();
      S.newGroupName = '';
      S.isCreatingGroup = false;

      const clean = S.slugify(name);
      if (clean && !S.tree.hasOwnProperty(clean)) {
        S.tree[clean] = [];
        S.openGroups.push(clean);
        S._render();
      } else {
        S._render();
      }
    },

    // ═══════════════════════════════════
    //  DRAG & DROP
    // ═══════════════════════════════════

    dragStart(slug, group) {
      S._dragSlug = slug;
      S._dragGroup = group;
    },

    dragOver(e) {
      e.preventDefault();
      e.currentTarget.classList.add('bg-cyan-50');
    },

    dragLeave(e) {
      e.currentTarget.classList.remove('bg-cyan-50');
    },

    async drop(e, targetGroup) {
      e.preventDefault();
      e.currentTarget.classList.remove('bg-cyan-50');

      const slug = S._dragSlug;
      const fromGroup = S._dragGroup;
      S._dragSlug = null;
      S._dragGroup = null;

      if (!slug || fromGroup === undefined) return;
      if (fromGroup === targetGroup) {
        // Same group — could handle reorder, skip for now
        return;
      }

      // Find the page
      let page = null;
      if (S.tree[fromGroup]) {
        const idx = S.tree[fromGroup].findIndex(p => p.slug === slug);
        if (idx !== -1) {
          page = S.tree[fromGroup].splice(idx, 1)[0];
        }
      }

      if (!page) return;

      // Insert into target
      if (!S.tree[targetGroup]) S.tree[targetGroup] = [];
      S.tree[targetGroup].push(page);

      // Re-render optimistically
      S._render();

      // Build new labels
      const newLabels = (page.labels || []).filter(l => !l.startsWith('main:'));
      if (targetGroup !== 'uncategorized') {
        newLabels.push('main:' + targetGroup);
      }
      
      page.labels = newLabels;

      // Save to server
      try {
        const r = await fetch('/page/' + encodeURIComponent(slug), {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(page),
        });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        S._toast('success', 'Dipindahkan ke ' + targetGroup);
      } catch (e) {
        console.error('Move failed:', e);
        S._toast('error', 'Gagal memindahkan, memuat ulang...');
        await S.load();
      }
    },

    // ═══════════════════════════════════
    //  HELPERS
    // ═══════════════════════════════════

    slugify(text) {
      if (!text) return '';
      return text.toString().toLowerCase().trim()
        .replace(/[^\w\s-]/g, '')
        .replace(/\s+/g, '-');
    },

    _toast(type, msg) {
      window.dispatchEvent(new CustomEvent('anita:toast', { detail: { type, message: msg } }));
    },

    // ═══════════════════════════════════
    //  RENDER
    // ═══════════════════════════════════

    _render() {
      const container = Q('#sm-tree');
      if (!container) return;

      let html = '';

      // Render each group
      Object.keys(S.tree).forEach(groupName => {
        const pages = S.tree[groupName] || [];
        const isOpen = S.openGroups.includes(groupName);
        const count = pages.length;

        html += `
          <div class="mb-4 border rounded-lg bg-white shadow-sm">
            <!-- Group Header -->
            <div class="flex items-center justify-between p-3 bg-gray-50 rounded-t-lg cursor-pointer"
                 data-sm-action="toggle-group" data-sm-group="${groupName}">
              <div class="flex items-center gap-2">
                <i class="fas fa-${isOpen ? 'folder-open' : 'folder'} text-yellow-500 text-sm"></i>
                <span class="font-medium text-sm capitalize">${groupName}</span>
                <span class="text-xs text-gray-400">(${count})</span>
              </div>
              <i class="fas fa-chevron-${isOpen ? 'down' : 'right'} text-xs text-gray-400"></i>
            </div>

            <!-- Group Body -->
            ${isOpen ? `
              <div class="divide-y"
                   data-sm-drop="${groupName}"
                   ondragover="StructureManager.dragOver(event)"
                   ondragleave="StructureManager.dragLeave(event)"
                   ondrop="StructureManager.drop(event, '${groupName}')"
                   style="min-height: ${count === 0 ? '60px' : 'auto'}">
                ${count === 0 ? `
                  <div class="p-4 text-center text-xs text-gray-400">
                    <i class="fas fa-inbox mb-1 block text-lg"></i>
                    Drop halaman di sini
                  </div>
                ` : pages.map((page) => {
                  
                  // Evaluate Status Variables
                  const isPublic = (page.labels || []).includes('any:read');
                  const isHome = (page.labels || []).includes('sys:home');
                  const isTemplate = (page.labels || []).includes('sys:template');
                  const isHead = (page.labels || []).includes('sys:head');

                  return `
                  <div class="flex items-center gap-3 p-3 hover:bg-gray-50 cursor-grab active:cursor-grabbing transition-colors group"
                       draggable="true"
                       data-sm-page="${page.slug}"
                       ondragstart="StructureManager.dragStart('${page.slug}', '${groupName}')">
                    <i class="fas fa-grip-vertical text-gray-300 text-xs"></i>
                    
                    <div class="flex-1 min-w-0">
                      <div class="text-sm font-medium truncate">${page.title || '(tanpa judul)'}</div>
                      <div class="text-[11px] text-gray-400">/${page.slug}</div>
                    </div>

                    <!-- Card Toggles -->
                    <div class="flex items-center gap-4 border-r border-gray-200 pr-4 mr-1 opacity-60 group-hover:opacity-100 transition-opacity">
                      
                      <!-- Public Toggle -->
                      <div class="flex items-center gap-1.5" title="Public Access (any:read)">
                        <button data-sm-action="toggle-label" data-sm-slug="${page.slug}" data-sm-label="any:read"
                                class="relative inline-flex h-4 w-7 items-center rounded-full transition-colors focus:outline-none ${isPublic ? 'bg-green-500' : 'bg-gray-300'}">
                          <span class="pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow-sm transition-transform ${isPublic ? 'translate-x-3.5' : 'translate-x-0.5'}"></span>
                        </button>
                        <span class="text-[11px] select-none ${isPublic ? 'text-gray-800 font-medium' : 'text-gray-400'}">Public</span>
                      </div>

                      <!-- Home Toggle -->
                      <div class="flex items-center gap-1.5" title="Set as Homepage (sys:home)">
                        <button data-sm-action="toggle-label" data-sm-slug="${page.slug}" data-sm-label="sys:home"
                                class="relative inline-flex h-4 w-7 items-center rounded-full transition-colors focus:outline-none ${isHome ? 'bg-blue-500' : 'bg-gray-300'}">
                          <span class="pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow-sm transition-transform ${isHome ? 'translate-x-3.5' : 'translate-x-0.5'}"></span>
                        </button>
                        <span class="text-[11px] select-none ${isHome ? 'text-gray-800 font-medium' : 'text-gray-400'}">Home</span>
                      </div>

                      <!-- Template Toggle -->
                      <div class="flex items-center gap-1.5" title="Set as Template (sys:template)">
                        <button data-sm-action="toggle-label" data-sm-slug="${page.slug}" data-sm-label="sys:template"
                                class="relative inline-flex h-4 w-7 items-center rounded-full transition-colors focus:outline-none ${isTemplate ? 'bg-purple-500' : 'bg-gray-300'}">
                          <span class="pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow-sm transition-transform ${isTemplate ? 'translate-x-3.5' : 'translate-x-0.5'}"></span>
                        </button>
                        <span class="text-[11px] select-none ${isTemplate ? 'text-gray-800 font-medium' : 'text-gray-400'}">Template</span>
                      </div>

                      <!-- Head Toggle (NEW) -->
                      <div class="flex items-center gap-1.5" title="Include in Head (sys:head)">
                        <button data-sm-action="toggle-label" data-sm-slug="${page.slug}" data-sm-label="sys:head"
                                class="relative inline-flex h-4 w-7 items-center rounded-full transition-colors focus:outline-none ${isHead ? 'bg-orange-500' : 'bg-gray-300'}">
                          <span class="pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow-sm transition-transform ${isHead ? 'translate-x-3.5' : 'translate-x-0.5'}"></span>
                        </button>
                        <span class="text-[11px] select-none ${isHead ? 'text-gray-800 font-medium' : 'text-gray-400'}">Head</span>
                      </div>

                    </div>

                    <!-- Type Badge -->
                    <span class="text-[10px] px-2 py-0.5 rounded font-medium ${page.type === 'html' ? 'bg-blue-100 text-blue-700' : 'bg-fuchsia-100 text-fuchsia-700'}">
                      ${page.type || 'md'}
                    </span>
                  </div>
                `}).join('')}
              </div>
            ` : ''}
          </div>`;
      });

      // New group button / input
      if (S.isCreatingGroup) {
        html += `
          <div class="flex items-center gap-2 p-3 border rounded-lg bg-white shadow-sm">
            <i class="fas fa-folder-plus text-yellow-500 text-sm"></i>
            <input id="sm-new-group-input" type="text"
                   class="flex-1 border-0 focus:ring-0 px-2 py-1 text-sm bg-transparent"
                   placeholder="Nama kelompok baru...">
            <button data-sm-action="confirm-new-group"
                    class="text-xs bg-cyan-600 hover:bg-cyan-700 text-white px-3 py-1.5 rounded transition-colors">Simpan</button>
            <button data-sm-action="cancel-new-group"
                    class="text-xs border border-gray-300 hover:bg-gray-50 px-3 py-1.5 rounded transition-colors">Batal</button>
          </div>`;
      } else {
        html += `
          <button id="sm-new-group-btn" 
                  data-sm-action="create-new-group"
                  class="w-full border-2 border-dashed border-gray-300 rounded-lg p-3 text-sm text-gray-500 hover:border-cyan-400 hover:text-cyan-600 hover:bg-cyan-50 transition-all font-medium">
            <i class="fas fa-plus mr-1"></i> Kelompok Baru
          </button>`;
      }

      container.innerHTML = html;
    }
  };

  document.addEventListener('DOMContentLoaded', () => S.init());
  window.StructureManager = S;
})();