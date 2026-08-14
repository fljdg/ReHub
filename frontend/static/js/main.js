// ReHub — base frontend JS
// Handles the responsive sidebar toggle. Add page-specific JS
// in a separate file and include it via {% block extra_js %}.

document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('sidebarToggle');
  const sidebar = document.querySelector('.sidebar');

  if (toggle && sidebar) {
    toggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });
  }
});