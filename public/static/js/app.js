document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('appSidebar');
  const overlay = document.getElementById('sidebarOverlay');
  const openButton = document.getElementById('sidebarOpen');
  const closeButton = document.getElementById('sidebarClose');
  const setSidebar = (open) => {
    if (!sidebar) return;
    sidebar.classList.toggle('is-open', open);
    overlay?.classList.toggle('is-open', open);
    openButton?.setAttribute('aria-expanded', String(open));
    document.body.style.overflow = open ? 'hidden' : '';
  };
  openButton?.addEventListener('click', () => setSidebar(true));
  closeButton?.addEventListener('click', () => setSidebar(false));
  overlay?.addEventListener('click', () => setSidebar(false));
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') setSidebar(false); });
  window.addEventListener('resize', () => { if (window.innerWidth >= 992) setSidebar(false); });
  document.querySelectorAll('[data-password-toggle]').forEach((button) => {
    button.addEventListener('click', () => {
      const input = document.getElementById(button.dataset.passwordToggle);
      if (!input) return;
      const showing = input.type === 'password';
      input.type = showing ? 'text' : 'password';
      button.setAttribute('aria-pressed', String(showing));
      button.setAttribute('aria-label', showing ? 'Hide password' : 'Show password');
      button.innerHTML = showing ? '<i class="bi bi-eye-slash"></i>' : '<i class="bi bi-eye"></i>';
    });
  });
});
