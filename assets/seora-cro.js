/* ŚEORA - product page section helpers (CTA buttons, FAQ single-open) */
(function () {
  if (window.__seoraCro) return;
  window.__seoraCro = true;

  function buyBox() {
    return document.querySelector('seora-product-info') || document.querySelector('product-info') || document.querySelector('.product__info-container');
  }
  function submitButton() {
    var box = buyBox();
    return (box && box.querySelector('button[name="add"]')) || document.querySelector('product-form button[name="add"]');
  }
  function scrollToPicker() {
    var box = buyBox();
    if (!box) return;
    var target = box.querySelector('.spi-picker, variant-radios, variant-selects, .product-form__input') || box;
    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    target.classList.remove('scro-flash');
    void target.offsetWidth;
    target.classList.add('scro-flash');
    setTimeout(function () { target.classList.remove('scro-flash'); }, 3000);
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest && e.target.closest('[data-scro-cta]');
    if (!btn) return;
    e.preventDefault();
    var mode = btn.getAttribute('data-scro-cta');
    var submit = submitButton();
    if (mode === 'add' && submit && !submit.disabled && submit.getAttribute('aria-disabled') !== 'true') {
      btn.classList.add('is-loading');
      submit.click();
      setTimeout(function () { btn.classList.remove('is-loading'); }, 1600);
      return;
    }
    scrollToPicker();
  });

  document.addEventListener('toggle', function (e) {
    var d = e.target;
    if (!d || d.tagName !== 'DETAILS' || !d.open) return;
    var group = d.closest('[data-scro-single]');
    if (!group) return;
    group.querySelectorAll('details[open]').forEach(function (other) { if (other !== d) other.open = false; });
  }, true);
})();
