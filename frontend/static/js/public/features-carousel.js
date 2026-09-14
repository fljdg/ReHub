// BLOCK: FEATURES — arrow-controlled horizontal scroll (mobile only,
// desktop shows all 3 cards side by side via CSS grid).
// Pairs with partials/public/features.html + css/public/features.css

document.addEventListener('DOMContentLoaded', () => {
  const track = document.getElementById('featuresTrack');
  const prev = document.getElementById('featuresPrev');
  const next = document.getElementById('featuresNext');

  if (!track || !prev || !next) return;

  const scrollByCard = (direction) => {
    const card = track.querySelector('.pub-feature-card');
    const amount = card ? card.getBoundingClientRect().width + 20 : 260;
    track.scrollBy({ left: direction * amount, behavior: 'smooth' });
  };

  prev.addEventListener('click', () => scrollByCard(-1));
  next.addEventListener('click', () => scrollByCard(1));
});
