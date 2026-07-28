/**
 * ConfigManager — Vanilla JS, zero dependencies.
 * Loads system config from /config/ and saves changes.
 */
(function () {
  'use strict';

  const Q = (s, c) => (c || document).querySelector(s);
  const QA = (s, c) => (c || document).querySelectorAll(s); 
  const C = {
    loading: false,
    saving: false,

    async init() {
      Q('#cfg-save')?.addEventListener('click', () => C.save());
      await C.load();
    },

    async load() {
      C.loading = true;
      C._setFormDisabled(true);

      try {
        const r = await fetch('/config/');
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const data = await r.json();

        // ── AI / General ──
        Q('#cfg-ai-endpoint').value = data.ai_endpoint || '';
        Q('#cfg-base-llm').value = data.base_llm || '';
        Q('#cfg-temperature').value = data.temperature !== undefined ? data.temperature : 0.7;
        Q('#cfg-system-note').value = data.system_note || '';
        Q('#cfg-theme').value = data.theme || 'default';

        // ── PocketBase ──
        Q('#cfg-pb-url').value = data.pb_url || '';
        Q('#cfg-pb-email').value = data.pb_admin_email || '';
        Q('#cfg-pb-password').value = '';        // never populate

        // ── Midtrans ──
        // ── Midtrans ──
        Q('#cfg-midtrans-key').value = data.midtrans_server_key || '';
        Q('#cfg-midtrans-merchant').value = data.midtrans_merchant_id || '';
        Q('#cfg-midtrans-production').checked = data.midtrans_is_production || false;
        Q('#cfg-midtrans-notify').value = data.midtrans_notification_url || '';

        // ── Midtrans — Payment Pipeline ──
        Q('#cfg-midtrans-order-prefix').value = data.midtrans_order_prefix || 'ORD-';
        Q('#cfg-midtrans-user-collection').value = data.midtrans_user_collection || 'users';
        Q('#cfg-midtrans-txn-collection').value = data.midtrans_transaction_collection || 'transactions';
        Q('#cfg-midtrans-reg-collection').value = data.midtrans_registration_collection || 'registrations';

        // ── AI Key (never populate) ──
        Q('#cfg-ai-key').value = '';

      } catch (e) {
        console.error('Config load failed:', e);
        C._toast('error', 'Gagal memuat konfigurasi');
      } finally {
        C.loading = false;
        C._setFormDisabled(false);
      }
    },

    async save() {
      C.saving = true;
      const btn = Q('#cfg-save');
      const origText = btn.textContent;
      btn.textContent = 'Menyimpan...';
      btn.disabled = true;

      const payload = {
        // ── AI / General ──
        ai_endpoint:   Q('#cfg-ai-endpoint').value.trim(),
        base_llm:      Q('#cfg-base-llm').value.trim(),
        temperature:   parseFloat(Q('#cfg-temperature').value) || 0.7,
        system_note:   Q('#cfg-system-note').value.trim(),
        theme:         Q('#cfg-theme').value.trim(),
        routes:        [],   // managed elsewhere or keep as-is

        // ── PocketBase ──
        pb_url:          Q('#cfg-pb-url').value.trim(),
        pb_admin_email:  Q('#cfg-pb-email').value.trim(),
        pb_admin_password: Q('#cfg-pb-password').value,

        // ── Midtrans ──
        midtrans_server_key:       Q('#cfg-midtrans-key').value.trim(),
        midtrans_merchant_id:      Q('#cfg-midtrans-merchant').value.trim(),
        midtrans_is_production:    Q('#cfg-midtrans-production').checked,
        midtrans_notification_url: Q('#cfg-midtrans-notify').value.trim(),

        // ── Midtrans — Payment Pipeline ──
        midtrans_order_prefix:              Q('#cfg-midtrans-order-prefix').value.trim() || 'ORD-',
        midtrans_user_collection:           Q('#cfg-midtrans-user-collection').value.trim() || 'users',
        midtrans_transaction_collection:    Q('#cfg-midtrans-txn-collection').value.trim() || 'transactions',
        midtrans_registration_collection:   Q('#cfg-midtrans-reg-collection').value.trim() || 'registrations',
      };

      // Strip empty secrets so backend keeps existing values
      if (!payload.ai_key || !payload.ai_key.trim()) {
        delete payload.ai_key;
      } else {
        payload.ai_key = Q('#cfg-ai-key').value.trim();
      }

      // ai_key wasn't in the payload — add it if filled
      const aiKey = Q('#cfg-ai-key').value.trim();
      if (aiKey) payload.ai_key = aiKey;

      if (!payload.pb_admin_password || !payload.pb_admin_password.trim()) {
        delete payload.pb_admin_password;
      }

      try {
        const r = await fetch('/config/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!r.ok) throw new Error('HTTP ' + r.status);

        // Success feedback
        btn.textContent = '✓ Tersimpan!';
        btn.classList.add('bg-green-600');
        setTimeout(() => {
          btn.textContent = origText;
          btn.classList.remove('bg-green-600');
          btn.disabled = false;
        }, 2000);

        C._toast('success', 'Konfigurasi disimpan~');

        // Clear password fields
        Q('#cfg-pb-password').value = '';
        Q('#cfg-ai-key').value = '';

      } catch (e) {
        console.error('Config save failed:', e);
        C._toast('error', 'Gagal menyimpan: ' + e.message);
        btn.textContent = origText;
        btn.disabled = false;
      } finally {
        C.saving = false;
      }
    },

    _setFormDisabled(disabled) {
      const fields = QA('input, textarea, select, button', Q('#cfg-form'));
      fields.forEach(f => { f.disabled = disabled; });
    },

    _toast(type, msg) {
      window.dispatchEvent(new CustomEvent('anita:toast', { detail: { type, message: msg } }));
    }
  };

  document.addEventListener('DOMContentLoaded', () => C.init());
  window.ConfigManager = C;
})();
