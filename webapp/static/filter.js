document.addEventListener('DOMContentLoaded', function() {
  const filterInput = document.getElementById('productFilter');
  const productCards = document.querySelectorAll('[data-product-name]');
  const noResultsMsg = document.getElementById('noFilterResults');

  if (!filterInput) return;

  filterInput.addEventListener('input', function() {
    const filterText = this.value.toLowerCase().trim();
    let visibleCount = 0;

    productCards.forEach(card => {
      const name = (card.getAttribute('data-product-name') || '').toLowerCase();
      const desc = (card.getAttribute('data-product-desc') || '').toLowerCase();
      
      const matches = !filterText || name.includes(filterText) || desc.includes(filterText);
      card.style.display = matches ? '' : 'none';
      if (matches) visibleCount++;
    });

    if (noResultsMsg) {
      noResultsMsg.style.display = visibleCount === 0 ? 'block' : 'none';
    }
  });
});
