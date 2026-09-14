// BLOCK: NAVBAR — mobile menu toggle
// Pairs with partials/public/navbar.html + css/public/navbar.css

document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('pubNavToggle');
  const links = document.getElementById('pubNavLinks');

  if (!toggle || !links) return;

  toggle.addEventListener('click', () => {
    const isOpen = links.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  });

  // Close the mobile menu after a link is tapped
  links.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      links.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
    });
  });
});
