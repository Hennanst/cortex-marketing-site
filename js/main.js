/* ══════════════════════════════════════════════════════════
   Setup Cortex — Main JavaScript
   ══════════════════════════════════════════════════════════ */

(function() {
  'use strict';

  // ── Navbar scroll effect ──
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    let lastScroll = 0;
    window.addEventListener('scroll', () => {
      const current = window.scrollY;
      if (current > 50) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }
      lastScroll = current;
    }, { passive: true });
  }

  // ── Mobile menu toggle ──
  const menuToggle = document.querySelector('.menu-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (menuToggle && navLinks) {
    menuToggle.addEventListener('click', () => {
      navLinks.classList.toggle('open');
      const isOpen = navLinks.classList.contains('open');
      menuToggle.innerHTML = isOpen ? '✕' : '☰';
      menuToggle.setAttribute('aria-expanded', isOpen);
    });

    // Close on link click
    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        navLinks.classList.remove('open');
        menuToggle.innerHTML = '☰';
      });
    });
  }

  // ── Fade-in on scroll (Intersection Observer) ──
  const fadeElements = document.querySelectorAll('.fade-in');
  if (fadeElements.length > 0 && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    });

    fadeElements.forEach(el => observer.observe(el));
  }

  // ── Score bar animation ──
  const scoreBars = document.querySelectorAll('.score-bar-fill');
  if (scoreBars.length > 0 && 'IntersectionObserver' in window) {
    const barObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const width = entry.target.getAttribute('data-width');
          entry.target.style.width = width + '%';
          barObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });

    scoreBars.forEach(bar => {
      bar.style.width = '0%';
      barObserver.observe(bar);
    });
  }

  // ── Setup Builder ──
  const budgetCards = document.querySelectorAll('.budget-card');
  const setupResults = document.querySelectorAll('.setup-result');

  budgetCards.forEach(card => {
    card.addEventListener('click', () => {
      // Remove active from all
      budgetCards.forEach(c => c.classList.remove('active'));
      setupResults.forEach(r => r.classList.remove('visible'));

      // Activate clicked
      card.classList.add('active');
      const budget = card.getAttribute('data-budget');
      const result = document.getElementById('setup-' + budget);
      if (result) {
        result.classList.add('visible');
        result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    });
  });

  // ── Smooth scroll for anchor links ──
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        const headerOffset = 80;
        const elementPosition = target.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.scrollY - headerOffset;
        window.scrollTo({ top: offsetPosition, behavior: 'smooth' });
      }
    });
  });

  // ── Category filter (for category pages) ──
  const filterBtns = document.querySelectorAll('.filter-btn');
  const productCards = document.querySelectorAll('.product-card[data-price]');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const filter = btn.getAttribute('data-filter');
      productCards.forEach(card => {
        if (filter === 'all') {
          card.style.display = '';
          return;
        }
        const price = parseFloat(card.getAttribute('data-price'));
        let show = false;
        switch(filter) {
          case 'budget': show = price < 200; break;
          case 'mid': show = price >= 200 && price < 500; break;
          case 'premium': show = price >= 500; break;
        }
        card.style.display = show ? '' : 'none';
      });
    });
  });

  // ── Sort products ──
  const sortSelect = document.querySelector('#sort-products');
  const productsGrid = document.querySelector('.products-grid');

  if (sortSelect && productsGrid) {
    sortSelect.addEventListener('change', () => {
      const cards = Array.from(productsGrid.querySelectorAll('.product-card'));
      const sortBy = sortSelect.value;

      cards.sort((a, b) => {
        switch(sortBy) {
          case 'score-desc':
            return (parseFloat(b.dataset.score) || 0) - (parseFloat(a.dataset.score) || 0);
          case 'price-asc':
            return (parseFloat(a.dataset.price) || 0) - (parseFloat(b.dataset.price) || 0);
          case 'price-desc':
            return (parseFloat(b.dataset.price) || 0) - (parseFloat(a.dataset.price) || 0);
          case 'rating-desc':
            return (parseFloat(b.dataset.rating) || 0) - (parseFloat(a.dataset.rating) || 0);
          default:
            return 0;
        }
      });

      cards.forEach(card => productsGrid.appendChild(card));
    });
  }

  // ── Amazon link tracking — Google Ads Conversion + Analytics ──
  document.querySelectorAll('a[href*="amazon.com.br"]').forEach(link => {
    link.addEventListener('click', function(e) {
      const productId = link.getAttribute('data-product') || '';
      const linkUrl = link.href;

      // Google Analytics 4 — event tracking
      if (typeof gtag === 'function') {
        gtag('event', 'click_amazon', {
          event_category: 'affiliate',
          event_label: productId || linkUrl,
          value: 1,
        });

        // Google Ads Conversion Event
        const conversionId = document.querySelector('meta[name="google-ads-conversion"]');
        if (conversionId && conversionId.content) {
          gtag('event', 'conversion', {
            send_to: conversionId.content,
            value: 1.0,
            currency: 'BRL',
            transaction_id: productId || ''
          });
        }
      }

      // Facebook Pixel
      if (typeof fbq === 'function') {
        fbq('track', 'InitiateCheckout', {
          content_ids: [productId],
          content_type: 'product',
        });
      }
    });
  });

  // ── Google Ads Landing Page Quality Signals ──
  // Track time on page (engagement signal)
  let engagementTime = 0;
  const engagementInterval = setInterval(() => {
    engagementTime += 1;
    if (engagementTime >= 30 && typeof gtag === 'function') {
      gtag('event', 'engaged_visit', {
        event_category: 'engagement',
        value: engagementTime,
      });
      clearInterval(engagementInterval);
    }
  }, 1000);

  // Track scroll depth
  let maxScroll = 0;
  window.addEventListener('scroll', () => {
    const scrollPercent = Math.round(
      (window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100
    );
    if (scrollPercent > maxScroll) {
      maxScroll = scrollPercent;
      if (maxScroll >= 75 && typeof gtag === 'function') {
        gtag('event', 'deep_scroll', {
          event_category: 'engagement',
          event_label: window.location.pathname,
          value: maxScroll,
        });
      }
    }
  }, { passive: true });

  // ── Back to top button ──
  const backToTop = document.querySelector('.back-to-top');
  if (backToTop) {
    window.addEventListener('scroll', () => {
      backToTop.classList.toggle('visible', window.scrollY > 500);
    }, { passive: true });

    backToTop.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // ── Reading progress bar (review pages) ──
  const progressBar = document.querySelector('.reading-progress');
  if (progressBar) {
    window.addEventListener('scroll', () => {
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const scrolled = (window.scrollY / docHeight) * 100;
      progressBar.style.width = Math.min(scrolled, 100) + '%';
    }, { passive: true });
  }

  // ── Copy link button ──
  document.querySelectorAll('.copy-link').forEach(btn => {
    btn.addEventListener('click', () => {
      navigator.clipboard.writeText(window.location.href).then(() => {
        const originalText = btn.textContent;
        btn.textContent = '✓ Copiado!';
        setTimeout(() => { btn.textContent = originalText; }, 2000);
      });
    });
  });

  // ── Image lazy loading fallback ──
  if (!('loading' in HTMLImageElement.prototype)) {
    const lazyImages = document.querySelectorAll('img[loading="lazy"]');
    const imgObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          img.src = img.dataset.src || img.src;
          imgObserver.unobserve(img);
        }
      });
    });
    lazyImages.forEach(img => imgObserver.observe(img));
  }

  // ═══════════════════════════════════════════════
  // SEARCH — real-time product search
  // ═══════════════════════════════════════════════
  const BP = window.__BASE_PATH__ || '';
  const products = window.__PRODUCTS__ || [];

  function initSearch(inputId, resultsId) {
    const input = document.getElementById(inputId);
    const results = document.getElementById(resultsId);
    if (!input || !results || products.length === 0) return;

    let debounce;
    input.addEventListener('input', function() {
      clearTimeout(debounce);
      debounce = setTimeout(() => {
        const q = this.value.trim().toLowerCase();
        if (q.length < 2) { results.classList.remove('active'); results.innerHTML = ''; return; }

        const terms = q.split(/\s+/);
        const matches = products.filter(p => {
          const txt = (p.t + ' ' + p.c).toLowerCase();
          return terms.every(t => txt.includes(t));
        }).slice(0, 8);

        if (matches.length === 0) {
          results.innerHTML = '<div class="search-no-results">Nenhum produto encontrado. Tente outro termo.</div>';
          results.classList.add('active');
          return;
        }

        results.innerHTML = matches.map(p => {
          const price = p.p > 0 ? 'R$ ' + p.p.toLocaleString('pt-BR', {minimumFractionDigits: 2}) : '';
          const cat = (p.c || '').replace(/_/g, ' ').replace(/-/g, ' ');
          return '<a href="' + BP + '/review/' + p.a + '.html" class="search-result-item">' +
            (p.i ? '<img src="' + p.i + '" alt="" loading="lazy">' : '') +
            '<div class="info"><div class="title">' + p.t + '</div><div class="meta">' + cat + '</div></div>' +
            (price ? '<span class="price-tag">' + price + '</span>' : '') +
            '</a>';
        }).join('');
        results.classList.add('active');
      }, 200);
    });

    // close on click outside
    document.addEventListener('click', function(e) {
      if (!input.contains(e.target) && !results.contains(e.target)) {
        results.classList.remove('active');
      }
    });

    // close on Escape
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') { results.classList.remove('active'); this.blur(); }
    });
  }

  initSearch('search-input', 'search-results');
  initSearch('hero-search', 'hero-search-results');

  // ═══════════════════════════════════════════════
  // CUSTOM BUDGET BUILDER — dynamic setup builder
  // ═══════════════════════════════════════════════
  const budgetDist = window.__BUDGET_DIST__ || {
    'placas-de-video': 0.25, 'processadores': 0.15, 'monitores-gamer': 0.15,
    'memoria-ram': 0.06, 'armazenamento': 0.06, 'fontes': 0.05, 'gabinetes': 0.05,
    'mouses-gamer': 0.04, 'teclados-mecanicos': 0.05, 'headsets-gamer': 0.05,
    'cadeiras-gamer': 0.06, 'perifericos': 0.03
  };

  const catLabels = {
    'placas-de-video': '🎮 Placa de Vídeo', 'processadores': '🧠 Processador',
    'monitores-gamer': '🖥️ Monitor', 'memoria-ram': '🧩 Memória RAM',
    'armazenamento': '💾 SSD', 'fontes': '⚡ Fonte', 'gabinetes': '🗄️ Gabinete',
    'mouses-gamer': '🖱️ Mouse', 'teclados-mecanicos': '⌨️ Teclado',
    'headsets-gamer': '🎧 Headset', 'cadeiras-gamer': '🪑 Cadeira',
    'perifericos': '🎯 Periféricos'
  };

  const catKw = {
    'mouses-gamer': ['mouse'], 'teclados-mecanicos': ['teclado','keyboard'],
    'monitores-gamer': ['monitor'], 'headsets-gamer': ['headset','fone','headphone'],
    'cadeiras-gamer': ['cadeira'], 'placas-de-video': ['placa de video','gpu','rtx','gtx','geforce','radeon'],
    'processadores': ['processador','cpu','ryzen','intel core','i5','i7'],
    'gabinetes': ['gabinete'], 'perifericos': ['mousepad','hub usb','apoio'],
    'armazenamento': ['ssd','nvme','hd externo','pendrive'],
    'memoria-ram': ['memoria ram','ram ddr','ram gamer'],
    'fontes': ['fonte gamer','fonte 80','fonte modular','fonte atx']
  };

  function findTop3(catSlug, maxPrice) {
    const kws = catKw[catSlug] || [catSlug.replace(/-/g, ' ')];
    const matches = products.filter(p => {
      if (p.p <= 0 || p.p > maxPrice) return false;
      const txt = (p.t + ' ' + (p.c || '')).toLowerCase();
      return kws.some(k => txt.includes(k));
    });
    matches.sort((a, b) => (b.r || 0) - (a.r || 0));
    return matches.slice(0, 3);
  }

  function buildCustomSetup(budget, resultElId) {
    const resultEl = document.getElementById(resultElId);
    if (!resultEl) return;

    let totalSpent = 0;
    let categories = [];

    for (const [cat, pct] of Object.entries(budgetDist)) {
      const maxP = Math.round(budget * pct);
      const top3 = findTop3(cat, maxP);
      const label = catLabels[cat] || cat;

      if (top3.length > 0) {
        totalSpent += top3[0].p;
        let optionsHtml = '';
        top3.forEach((p, idx) => {
          const badgeClass = idx === 0 ? 'option-best' : 'option-alt';
          const badgeLabel = idx === 0 ? '⭐ Melhor opção' : 'Opção ' + (idx + 1);
          optionsHtml +=
            '<div class="setup-option ' + badgeClass + '">' +
              '<span class="option-badge">' + badgeLabel + '</span>' +
              '<img src="' + p.i + '" alt="" loading="lazy">' +
              '<h4><a href="' + BP + '/review/' + p.a + '.html">' + p.t + '</a></h4>' +
              '<div class="option-meta">' +
                '<span class="price">R$ ' + p.p.toLocaleString('pt-BR', {minimumFractionDigits:2}) + '</span>' +
                '<span class="rating">★ ' + (p.r || 0).toFixed(1) + '</span>' +
              '</div>' +
              '<a href="' + p.l + '" target="_blank" rel="nofollow sponsored" class="btn btn-sm btn-amazon">🛒 Comprar</a>' +
            '</div>';
        });
        categories.push(
          '<div class="setup-category fade-in">' +
            '<div class="setup-cat-header">' +
              '<span class="cat-name">' + label + '</span>' +
              '<span class="cat-budget">até R$ ' + maxP.toLocaleString('pt-BR') + '</span>' +
            '</div>' +
            '<div class="setup-options">' + optionsHtml + '</div>' +
          '</div>'
        );
      } else {
        categories.push(
          '<div class="setup-category fade-in">' +
            '<div class="setup-cat-header">' +
              '<span class="cat-name">' + label + '</span>' +
              '<span class="cat-budget">até R$ ' + maxP.toLocaleString('pt-BR') + '</span>' +
            '</div>' +
            '<div class="setup-options">' +
              '<div class="setup-option option-empty"><p>Sem produto nessa faixa</p></div>' +
            '</div>' +
          '</div>'
        );
      }
    }

    const savings = budget - totalSpent;
    resultEl.innerHTML =
      '<div class="budget-result-header"><h3>🎮 Setup para R$ ' + budget.toLocaleString('pt-BR') + '</h3></div>' +
      '<div class="setup-grid">' + categories.join('') + '</div>' +
      '<div class="budget-result-total">' +
        '<div class="total-value">Total: R$ ' + totalSpent.toLocaleString('pt-BR', {minimumFractionDigits:2}) + '</div>' +
        (savings > 0 ? '<div class="total-savings">💰 Sobra: R$ ' + savings.toLocaleString('pt-BR', {minimumFractionDigits:2}) + ' para jogos!</div>' : '') +
      '</div>';
    resultEl.classList.add('active');
    resultEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // Trigger fade-in observer
    resultEl.querySelectorAll('.fade-in').forEach(el => el.classList.add('visible'));
  }

  // Wire up budget buttons on homepage
  function wireBudget(inputId, btnId, resultId) {
    const input = document.getElementById(inputId);
    const btn = document.getElementById(btnId);
    if (!input || !btn) return;

    btn.addEventListener('click', () => {
      const val = parseInt(input.value) || 5000;
      buildCustomSetup(Math.max(val, 500), resultId);
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') btn.click();
    });
  }

  wireBudget('custom-budget', 'budget-go-btn', 'custom-budget-result');
  wireBudget('custom-budget-setup', 'budget-go-setup', 'custom-budget-result-setup');

  // Budget presets
  document.querySelectorAll('.budget-preset').forEach(btn => {
    btn.addEventListener('click', function() {
      const val = parseInt(this.getAttribute('data-value'));
      const wrapper = this.closest('.budget-input-wrapper') || this.closest('section');
      const input = wrapper ? wrapper.querySelector('input[type="number"]') : null;
      if (input) { input.value = val; }
      // Find the closest result container
      const section = this.closest('section');
      const resultEl = section ? section.querySelector('.custom-budget-result') : null;
      if (resultEl) {
        buildCustomSetup(val, resultEl.id);
      }
    });
  });

})();
