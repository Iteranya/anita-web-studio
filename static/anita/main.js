// ── View → required script mapping ──
const VIEW_SCRIPTS = {
  dashboard:   '/anita/js/views/dashboard.js',
  page:        '/anita/js/views/page.js',
  media:       '/anita/js/views/media.js',
  users:       '/anita/js/views/users.js',
  config:      '/anita/js/views/config.js',
  structure:   '/anita/js/views/structure.js',
};

const loadedScripts = new Set();

// ── Load a script dynamically ──
function loadScript(src) {
  return new Promise((resolve) => {
    if (loadedScripts.has(src)) return resolve();
    const s = document.createElement('script');
    s.src = src;
    s.onload = () => { loadedScripts.add(src); resolve(); };
    s.onerror = () => resolve(); // fail silently
    document.head.appendChild(s);
  });
}

// ── Get current view slug from URL ──
function currentView() {
  return window.location.pathname.split('/').pop() || 'dashboard';
}

// ── SPA navigation (no page flash) ──
async function navigate(slug) {
  history.pushState({ slug }, '', `/anita/${slug}`);

  // Fetch view HTML
  const res = await fetch(`/anita/views/${slug}.html`);
  const html = await res.text();
  document.querySelector('main').innerHTML = html;

  // Highlight sidebar
  document.querySelectorAll('nav a').forEach(a => a.classList.remove('bg-gray-800'));
  const link = document.querySelector(`nav a[href="/anita/${slug}"]`);
  if (link) link.classList.add('bg-gray-800');

  // Load view script
  if (VIEW_SCRIPTS[slug]) await loadScript(VIEW_SCRIPTS[slug]);

  // Dispatch event so view scripts can re-init
  window.dispatchEvent(new CustomEvent('anita:view', { detail: { slug } }));
}

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  const slug = currentView();

  // Intercept sidebar clicks
  document.addEventListener('click', (e) => {
    const link = e.target.closest('nav a[href^="/anita/"]');
    if (!link) return;
    e.preventDefault();
    navigate(link.getAttribute('href').split('/').pop());
  });

  // Back/forward
  window.addEventListener('popstate', (e) => {
    if (e.state?.slug) navigate(e.state.slug);
  });

  // Load current view script
  if (VIEW_SCRIPTS[slug]) loadScript(VIEW_SCRIPTS[slug]);
});
