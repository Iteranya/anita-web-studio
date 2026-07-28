/**
 * UserManager — Vanilla JS, zero dependencies.
 * List users. Create admins. Change passwords. Delete.
 * No ABAC. No roles. No permissions.
 */
(function () {
  'use strict';

  const Q = (s, c) => (c || document).querySelector(s);
  const QA = (s, c) => (c || document).querySelectorAll(s);

  const U = {
    users: [],
    targetUser: null,

    async init() {
      Q('#um-new-user')?.addEventListener('click', () => U._openCreate());
      Q('#um-save-user')?.addEventListener('click', () => U._saveUser());
      Q('#um-cancel-user')?.addEventListener('click', () => U._closeUserModal());
      Q('#um-save-password')?.addEventListener('click', () => U._changePassword());
      Q('#um-cancel-password')?.addEventListener('click', () => U._closePasswordModal());
      Q('#um-confirm-delete')?.addEventListener('click', () => U._doDelete());
      Q('#um-cancel-delete')?.addEventListener('click', () => U._closeDeleteModal());

      await U.load();
    },

    async load() {
      try {
        const r = await fetch('/users/');
        if (!r.ok) throw new Error('HTTP ' + r.status);
        U.users = await r.json();
        U._render();
      } catch (e) {
        console.error('UserManager load failed:', e);
      }
    },

    // ── Create / Edit ──

    _openCreate(user) {
      U.targetUser = user || null;
      Q('#um-user-username').value = user ? user.username : '';
      Q('#um-user-display').value = user ? (user.display_name || '') : '';
      Q('#um-user-password').value = '';
      Q('#um-user-username').disabled = !!user;
      Q('#um-user-modal-title').textContent = user ? 'Edit User' : 'Buat Admin Baru';
      Q('#um-user-modal')?.classList.remove('hidden');
    },

    _closeUserModal() {
      Q('#um-user-modal')?.classList.add('hidden');
      U.targetUser = null;
    },

    async _saveUser() {
      const username = Q('#um-user-username').value.trim();
      const display = Q('#um-user-display').value.trim();
      const password = Q('#um-user-password').value;

      if (!username) return U._toast('error', 'Username wajib diisi');
      if (!U.targetUser && (!password || password.length < 8))
        return U._toast('error', 'Password minimal 8 karakter');

      try {
        let r;
        if (U.targetUser) {
          // Edit existing
          r = await fetch('/users/' + encodeURIComponent(U.targetUser.username), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ display_name: display, role: 'admin' }),
          });
        } else {
          // Create new
          r = await fetch('/users/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, display_name: display, password, role: 'admin' }),
          });
        }

        if (!r.ok) {
          const err = await r.text().catch(() => 'Unknown');
          throw new Error(err.slice(0, 200));
        }

        U._closeUserModal();
        await U.load();
        U._toast('success', U.targetUser ? 'User diperbarui~' : 'Admin baru dibuat~');
      } catch (e) {
        U._toast('error', 'Gagal: ' + e.message);
      }
    },

    // ── Password ──

    _openPassword(user) {
      U.targetUser = user;
      Q('#um-pw-username').textContent = user.username;
      Q('#um-pw-new').value = '';
      Q('#um-password-modal')?.classList.remove('hidden');
    },

    _closePasswordModal() {
      Q('#um-password-modal')?.classList.add('hidden');
      U.targetUser = null;
    },

    async _changePassword() {
      const pw = Q('#um-pw-new').value;
      if (!pw || pw.length < 8) return U._toast('error', 'Password minimal 8 karakter');

      try {
        const r = await fetch('/users/' + encodeURIComponent(U.targetUser.username) + '/password', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ new_password: pw }),
        });
        if (!r.ok) throw new Error('HTTP ' + r.status);

        U._closePasswordModal();
        U._toast('success', 'Password diperbarui~');
      } catch (e) {
        U._toast('error', 'Gagal: ' + e.message);
      }
    },

    // ── Delete ──

    _confirmDelete(user) {
      U.targetUser = user;
      Q('#um-delete-name').textContent = user.username;
      Q('#um-delete-modal')?.classList.remove('hidden');
    },

    _closeDeleteModal() {
      Q('#um-delete-modal')?.classList.add('hidden');
      U.targetUser = null;
    },

    async _doDelete() {
      if (!U.targetUser) return;
      try {
        const r = await fetch('/users/' + encodeURIComponent(U.targetUser.username), { method: 'DELETE' });
        if (!r.ok) {
          const err = await r.text().catch(() => 'Unknown');
          throw new Error(err.slice(0, 200));
        }
        U._closeDeleteModal();
        await U.load();
        U._toast('success', 'User dihapus~');
      } catch (e) {
        U._toast('error', 'Gagal: ' + e.message);
      }
    },

    // ── Render ──

    _render() {
      const tbody = Q('#um-table-body');
      if (!tbody) return;

      if (!U.users.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="p-4 text-center text-gray-400">Belum ada user~</td></tr>';
        return;
      }

      tbody.innerHTML = U.users.map(u => `
        <tr class="border-b hover:bg-gray-50">
          <td class="p-3 font-medium">${u.username}</td>
          <td class="p-3 text-sm">${u.display_name || '-'}</td>
          <td class="p-3 text-sm text-gray-500">${u.role || '-'}</td>
          <td class="p-3 text-right space-x-2">
            <button data-um-edit="${u.username}" class="text-xs text-gray-500 hover:text-cyan-600">Edit</button>
            <button data-um-password="${u.username}" class="text-xs text-gray-500 hover:text-yellow-600">Password</button>
            <button data-um-delete="${u.username}" class="text-xs text-red-400 hover:text-red-600">Hapus</button>
          </td>
        </tr>
      `).join('');

      // Bind buttons
      QA('[data-um-edit]', tbody).forEach(b => {
        b.addEventListener('click', () => {
          const user = U.users.find(u => u.username === b.dataset.umEdit);
          if (user) U._openCreate(user);
        });
      });
      QA('[data-um-password]', tbody).forEach(b => {
        b.addEventListener('click', () => {
          const user = U.users.find(u => u.username === b.dataset.umPassword);
          if (user) U._openPassword(user);
        });
      });
      QA('[data-um-delete]', tbody).forEach(b => {
        b.addEventListener('click', () => {
          const user = U.users.find(u => u.username === b.dataset.umDelete);
          if (user) U._confirmDelete(user);
        });
      });
    },

    _toast(type, msg) {
      window.dispatchEvent(new CustomEvent('anita:toast', { detail: { type, message: msg } }));
    }
  };

  document.addEventListener('DOMContentLoaded', () => U.init());
  window.UserManager = U;
})();
