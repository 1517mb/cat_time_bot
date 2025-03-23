document.addEventListener('DOMContentLoaded', () => {
  const $navbarBurgers = Array.prototype.slice.call(document.querySelectorAll('.navbar-burger'), 0);

  $navbarBurgers.forEach(el => {
    el.addEventListener('click', () => {
      const target = el.dataset.target;
      const $target = document.getElementById(target);

      if (!$target) {
        console.error('Target element not found:', target);
        return;
      }

      el.classList.toggle('is-active');
      $target.classList.toggle('is-active');
    });
  });
});