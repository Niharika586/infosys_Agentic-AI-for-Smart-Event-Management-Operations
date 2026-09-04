/* =================================================================
   RegisterAI — Global Frontend Script (script.js)
================================================================= */

document.addEventListener('DOMContentLoaded', function () {
  initLoadingScreen();
  initAOS();
  initNavToggle();
  initThemeToggle();
  initLiveClock();
  initScrollTop();
  initProfileMenu();
  initCounters();
  initToastAutoDismiss();
  initRegisterForm();
  setYear();
});

/* ---------------- Loading Screen ---------------- */
function initLoadingScreen() {
  const screen = document.getElementById('loadingScreen');
  if (!screen) return;
  window.addEventListener('load', () => {
    setTimeout(() => screen.classList.add('hide'), 500);
  });
  // Fallback in case 'load' already fired
  setTimeout(() => screen.classList.add('hide'), 2000);
}

/* ---------------- AOS Animations ---------------- */
function initAOS() {
  if (typeof AOS !== 'undefined') {
    AOS.init({ duration: 800, once: true, offset: 60, easing: 'ease-out-cubic' });
  }
}

/* ---------------- Mobile Nav Toggle ---------------- */
function initNavToggle() {
  const toggle = document.getElementById('navToggle');
  const links = document.getElementById('navLinks');
  if (!toggle || !links) return;
  toggle.addEventListener('click', () => links.classList.toggle('show'));
  links.querySelectorAll('a').forEach(a => a.addEventListener('click', () => links.classList.remove('show')));
}

/* ---------------- Theme Toggle (Dark / Light) ---------------- */
function initThemeToggle() {
  const btn = document.getElementById('themeToggle');
  if (!btn) return;

  const saved = window.__theme || 'dark';
  applyTheme(saved);

  btn.addEventListener('click', () => {
    const isLight = document.body.classList.toggle('light-theme');
    window.__theme = isLight ? 'light' : 'dark';
    btn.innerHTML = isLight ? '<i class="fa-solid fa-sun"></i>' : '<i class="fa-solid fa-moon"></i>';
  });

  function applyTheme(theme) {
    if (theme === 'light') {
      document.body.classList.add('light-theme');
      btn.innerHTML = '<i class="fa-solid fa-sun"></i>';
    } else {
      btn.innerHTML = '<i class="fa-solid fa-moon"></i>';
    }
  }
}

/* ---------------- Live Clock ---------------- */
function initLiveClock() {
  const el = document.getElementById('clockText');
  if (!el) return;
  function tick() {
    const now = new Date();
    el.textContent = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
  tick();
  setInterval(tick, 1000);
}

/* ---------------- Scroll To Top ---------------- */
function initScrollTop() {
  const btn = document.getElementById('scrollTopBtn');
  if (!btn) return;
  window.addEventListener('scroll', () => {
    btn.classList.toggle('show', window.scrollY > 400);
  });
  btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}

/* ---------------- Profile Dropdown Menu ---------------- */
function initProfileMenu() {
  const btn = document.getElementById('profileBtn');
  const dropdown = document.getElementById('profileDropdown');
  if (!btn || !dropdown) return;
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown.classList.toggle('show');
  });
  document.addEventListener('click', () => dropdown.classList.remove('show'));
}

/* ---------------- Animated Counters ---------------- */
function initCounters() {
  const counters = document.querySelectorAll('.counter');
  if (!counters.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.4 });

  counters.forEach(c => observer.observe(c));
}

function animateCounter(el) {
  const target = parseFloat(el.dataset.target) || 0;
  const duration = 1400;
  const start = performance.now();

  function update(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const value = Math.floor(eased * target);
    el.textContent = value;
    if (progress < 1) requestAnimationFrame(update);
    else el.textContent = target;
  }
  requestAnimationFrame(update);
}

/* ---------------- Toast Auto Dismiss ---------------- */
function initToastAutoDismiss() {
  document.querySelectorAll('.toast').forEach(toast => {
    setTimeout(() => {
      toast.style.transition = 'opacity .4s ease, transform .4s ease';
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(120%)';
      setTimeout(() => toast.remove(), 400);
    }, 5000);
  });
}

/* ---------------- Footer Year ---------------- */
function setYear() {
  const el = document.getElementById('year');
  if (el) el.textContent = new Date().getFullYear();
}

/* =================================================================
   Registration Form Validation (client-side)
================================================================= */
function initRegisterForm() {
  const form = document.getElementById('registerForm');
  if (!form) return;

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const phoneRegex = /^[6-9]\d{9}$/;

  const nameInput = form.querySelector('#name');
  const emailInput = form.querySelector('#email');
  const phoneInput = form.querySelector('#phone');

  // Restrict phone to digits only
  if (phoneInput) {
    phoneInput.addEventListener('input', () => {
      phoneInput.value = phoneInput.value.replace(/\D/g, '').slice(0, 10);
    });
  }

  // Live duplicate email check
  if (emailInput) {
    let debounceTimer;
    emailInput.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      const group = emailInput.closest('.form-group');
      const errorEl = group.querySelector('.error-msg');
      if (!emailRegex.test(emailInput.value)) {
        errorEl.textContent = '';
        return;
      }
      debounceTimer = setTimeout(() => {
        fetch(`/api/check-email?email=${encodeURIComponent(emailInput.value)}`)
          .then(r => r.json())
          .then(data => {
            if (data.exists) {
              emailInput.classList.add('invalid');
              errorEl.textContent = 'This email is already registered.';
            } else {
              emailInput.classList.remove('invalid');
              errorEl.textContent = '';
            }
          }).catch(() => {});
      }, 500);
    });
  }

  form.addEventListener('submit', function (e) {
    let valid = true;

    form.querySelectorAll('[required]').forEach(field => {
      const group = field.closest('.form-group');
      if (!group) return;
      const errorEl = group.querySelector('.error-msg');

      if (field.type === 'radio') {
        const radios = form.querySelectorAll(`[name="${field.name}"]`);
        const checked = Array.from(radios).some(r => r.checked);
        if (!checked && errorEl) {
          errorEl.textContent = 'This field is required.';
          valid = false;
        } else if (errorEl) {
          errorEl.textContent = '';
        }
        return;
      }

      if (!field.value.trim()) {
        field.classList.add('invalid');
        if (errorEl) errorEl.textContent = 'This field is required.';
        valid = false;
      } else {
        field.classList.remove('invalid');
        if (errorEl) errorEl.textContent = '';
      }
    });

    if (nameInput && nameInput.value.trim().length < 3) {
      nameInput.classList.add('invalid');
      nameInput.closest('.form-group').querySelector('.error-msg').textContent = 'Name must be at least 3 characters.';
      valid = false;
    }

    if (emailInput && !emailRegex.test(emailInput.value)) {
      emailInput.classList.add('invalid');
      emailInput.closest('.form-group').querySelector('.error-msg').textContent = 'Enter a valid email address.';
      valid = false;
    }

    if (phoneInput && !phoneRegex.test(phoneInput.value)) {
      phoneInput.classList.add('invalid');
      phoneInput.closest('.form-group').querySelector('.error-msg').textContent = 'Enter a valid 10-digit phone number.';
      valid = false;
    }

    if (!valid) e.preventDefault();
  });
}
