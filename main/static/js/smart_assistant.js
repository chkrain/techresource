class SmartAssistant {
  constructor() {
    this.userBehavior = {
      startTime: Date.now(),
      currentPage: window.location.pathname,
      searchAttempts: 0,
      productViews: [],
      productViewTimes: {},
      cartItems: 0,
      scrollDepth: 0,
      formAttempts: 0,
      priceRangeAttempts: 0,
      visitedPages: [window.location.pathname],
    };
    this.knowledgeBase = {
      pages: {
        "/": { title: "Главная", desc: "АСУ ТП, инжиниринг", category: "main" },
        "/about/": {
          title: "О компании",
          desc: "13 лет опыта",
          category: "info",
        },
        "/contacts/": {
          title: "Контакты",
          desc: "+7 (937) 524-68-88",
          category: "contact",
        },
        "/products/": {
          title: "Каталог",
          desc: "Оборудование",
          category: "shop",
        },
        "/cart/": { title: "Корзина", desc: "Оформление", category: "shop" },
        "/wishlist/": {
          title: "Избранное",
          desc: "Сохраненные товары",
          category: "shop",
        },
        "/services/": {
          title: "Услуги",
          desc: "Проектирование, монтаж, ПО",
          category: "services",
        },
        "/technical-task/": {
          title: "Техзадание",
          desc: "Для расчета КП",
          category: "forms",
        },
        "/support/": {
          title: "Поддержка",
          desc: "Помощь",
          category: "support",
        },
        "/orders/": { title: "Заказы", desc: "История", category: "profile" },
        "/profile/": {
          title: "Профиль",
          desc: "Личные данные",
          category: "profile",
        },
      },
      services: {
        design: { title: "Проектирование", url: "/services/design/" },
        electrical: { title: "Монтаж", url: "/services/electrical/" },
        software: { title: "Разработка ПО", url: "/services/software/" },
        equipment: { title: "Поставка", url: "/services/equipment/" },
        support: { title: "Техподдержка", url: "/services/support/" },
        maintenance: { title: "Обслуживание", url: "/services/maintenance/" },
        turnkey: { title: "Под ключ", url: "/services/turnkey/" },
      },
    };
    this.init();
  }
  async init() {
    await this.getCartCount();
    this.trackAll();
    this.createFloatingButton();
    this.initHotkeys();
  }
  async getCartCount() {
    try {
      const response = await fetch("/cart/api/count/");
      const data = await response.json();
      this.userBehavior.cartItems = data.count || 0;
    } catch (e) {
      const badge = document.querySelector(".cart-badge");
      if (badge) this.userBehavior.cartItems = parseInt(badge.textContent) || 0;
    }
  }
  trackAll() {
    this.trackPageViews();
    this.trackProductViews();
    this.trackSearch();
    this.trackScroll();
    this.trackTimeOnPage();
    this.trackExitIntent();
    this.trackFormAttempts();
    this.trackCartAbandonment();
    this.trackPriceFilter();
    this.trackServicePageBehavior();
  }
  trackPageViews() {
    let lastPath = window.location.pathname;
    const observer = new MutationObserver(() => {
      const newPath = window.location.pathname;
      if (newPath !== lastPath) {
        this.userBehavior.visitedPages.push(newPath);
        lastPath = newPath;
        this.analyzeNavigationPattern();
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }
  analyzeNavigationPattern() {
    const pages = this.userBehavior.visitedPages;
    if (
      pages.includes("/products/") &&
      pages.filter((p) => p.includes("/product/")).length >= 3
    ) {
      this.showSmartSuggestion({
        id: "product_comparison",
        title: "🤔 Сравнение товаров",
        message: "Чтобы выбрать лучшее, сравните характеристики",
        actions: [
          {
            text: "📊 Сравнить",
            url: "/products/compare/",
            icon: "fa-chart-line",
          },
          { text: "💬 Поможем выбрать", url: "/contacts/", icon: "fa-headset" },
        ],
        priority: "high",
      });
    }
    if (
      pages.includes("/services/") &&
      pages.length > 3 &&
      !pages.includes("/technical-task/")
    ) {
      this.showSmartSuggestion({
        id: "service_reminder",
        title: "🏗️ Нужен проект?",
        message: "Оставьте техзадание — рассчитаем стоимость",
        actions: [
          {
            text: "📝 Заполнить ТЗ",
            url: "/technical-task/",
            icon: "fa-file-alt",
          },
          { text: "📞 Позвонить", url: "tel:+79375246888", icon: "fa-phone" },
        ],
        priority: "medium",
      });
    }
  }
  trackProductViews() {
    const observer = new MutationObserver(() => {
      const productCards = document.querySelectorAll(
        ".product-card, .product-item, [data-product-id]",
      );
      productCards.forEach((card) => {
        if (!card.dataset.observed) {
          card.dataset.observed = "true";
          const link = card.querySelector("a");
          if (link) {
            link.addEventListener("click", () => {
              const productId = link.href?.split("/").pop();
              if (
                productId &&
                !this.userBehavior.productViews.includes(productId)
              ) {
                this.userBehavior.productViews.push(productId);
                this.userBehavior.productViewTimes[productId] = Date.now();
                this.analyzeProductViews();
              }
            });
          }
        }
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }
  analyzeProductViews() {
    const count = this.userBehavior.productViews.length;
    if (count === 3) {
      this.showSmartSuggestion({
        id: "basket_3_products",
        title: "🛍️ Комплексное предложение",
        message: "Соберем оборудование со скидкой до 15%",
        actions: [
          {
            text: "📋 Запросить КП",
            url: "/technical-task/",
            icon: "fa-file-invoice",
          },
          { text: "🛒 В корзину", url: "/cart/", icon: "fa-shopping-cart" },
        ],
        priority: "high",
      });
    }
    if (count >= 5) {
      this.showSmartSuggestion({
        id: "many_products",
        title: "🎯 Оптовый заказ",
        message: "Для крупных заказов — индивидуальные цены",
        actions: [
          {
            text: "💰 Узнать оптовую цену",
            url: "/contacts/",
            icon: "fa-ruble-sign",
          },
          {
            text: "📄 Скачать прайс",
            url: "/price-list/",
            icon: "fa-file-excel",
          },
        ],
        priority: "high",
      });
    }
  }
  trackSearch() {
    const searchInput = document.querySelector(
      'input[name="search"], input[type="search"]',
    );
    if (!searchInput) return;
    let failedQueries = [];
    let searchTimer;
    const performSearch = async () => {
      const query = searchInput.value.toLowerCase();
      if (query.length < 3) return;
      try {
        const response = await fetch(
          `/api/search-suggestions/?q=${encodeURIComponent(query)}`,
        );
        const data = await response.json();
        if (!data.results || data.results.length === 0) {
          failedQueries.push(query);
          if (failedQueries.length >= 2) {
            this.showSmartSuggestion({
              id: "search_failed",
              title: "🔍 Не нашли товар?",
              message: `"${query}"—возможно,естьаналог`,
              actions: [
                {
                  text: "📞 Запросить аналог",
                  url: "/technical-task/",
                  icon: "fa-file-alt",
                },
                {
                  text: "💬 Спросить инженера",
                  url: "/contacts/",
                  icon: "fa-headset",
                },
              ],
              priority: "high",
            });
            failedQueries = [];
          }
        } else {
          failedQueries = [];
        }
      } catch (e) {}
    };
    searchInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(performSearch, 500);
      }
    });
  }
  trackScroll() {
    let maxScroll = 0;
    let triggered = { product: false, services: false, contacts: false };
    window.addEventListener("scroll", () => {
      const scrollPercent =
        (window.scrollY /
          (document.documentElement.scrollHeight - window.innerHeight)) *
        100;
      if (scrollPercent > maxScroll) maxScroll = scrollPercent;
      if (
        window.location.pathname.includes("/product/") &&
        maxScroll > 80 &&
        !triggered.product
      ) {
        this.showSmartSuggestion({
          id: "product_scroll_end",
          title: "📦 Изучили товар?",
          message: "Готовы заказать или нужна консультация?",
          actions: [
            {
              text: "✅ В корзину",
              url: "#",
              action: "add_current_to_cart",
              icon: "fa-cart-plus",
            },
            {
              text: "🔧 Нужна установка",
              url: "/services/electrical/",
              icon: "fa-tools",
            },
          ],
          priority: "medium",
        });
        triggered.product = true;
      }
      if (
        window.location.pathname === "/services/" &&
        maxScroll > 60 &&
        !triggered.services
      ) {
        this.showSmartSuggestion({
          id: "services_scroll",
          title: "🏗️ Выберите услугу",
          message: "Какое направление вас интересует?",
          actions: [
            {
              text: "📐 Проектирование",
              url: "/services/design/",
              icon: "fa-drafting-compass",
            },
            {
              text: "⚡ Монтаж",
              url: "/services/electrical/",
              icon: "fa-bolt",
            },
            {
              text: "💻 Разработка ПО",
              url: "/services/software/",
              icon: "fa-code",
            },
          ],
          priority: "medium",
        });
        triggered.services = true;
      }
    });
  }
  trackTimeOnPage() {
    let timers = {};
    const checkPageTime = () => {
      const timeOnPage = (Date.now() - this.userBehavior.startTime) / 1000;
      const path = window.location.pathname;
      if (path.includes("/product/") && timeOnPage > 60 && !timers.product) {
        timers.product = true;
        this.showSmartSuggestion({
          id: "long_product_page",
          title: "⏳ Долго выбираете?",
          message: "Поможем определиться с характеристиками",
          actions: [
            {
              text: "🔧 Сравнить модели",
              url: "/products/",
              icon: "fa-chart-simple",
            },
            {
              text: "💡 Консультация",
              url: "/contacts/",
              icon: "fa-lightbulb",
            },
          ],
          priority: "medium",
        });
      }
      if (path === "/cart/" && timeOnPage > 45 && timers.cart === undefined) {
        timers.cart = true;
        if (this.userBehavior.cartItems > 0) {
          this.showSmartSuggestion({
            id: "cart_timeout",
            title: "🛒 Оформить заказ?",
            message: "Специальное предложение для вас!",
            actions: [
              {
                text: "✅ Перейти к оформлению",
                url: "/cart/checkout/",
                icon: "fa-credit-card",
              },
              {
                text: "📄 Запросить счет",
                url: "/technical-task/",
                icon: "fa-file-invoice",
              },
              {
                text: "🏷️ Промокод",
                url: "#",
                action: "show_promo",
                icon: "fa-tag",
              },
            ],
            priority: "high",
          });
        }
      }
      if (path === "/services/" && timeOnPage > 90 && !timers.services) {
        timers.services = true;
        this.showSmartSuggestion({
          id: "long_services",
          title: "🔍 Ищете решение?",
          message: "Расскажем о реализованных проектах",
          actions: [
            {
              text: "📊 Примеры работ",
              url: "/turnkey-projects/",
              icon: "fa-folder-open",
            },
            {
              text: "✍️ Заполнить ТЗ",
              url: "/technical-task/",
              icon: "fa-file-alt",
            },
          ],
          priority: "medium",
        });
      }
    };
    setInterval(checkPageTime, 10000);
  }
  trackExitIntent() {
    let exitShown = false;
    document.addEventListener("mouseleave", (e) => {
      if (
        e.clientY < 0 &&
        !exitShown &&
        !sessionStorage.getItem("exit_shown")
      ) {
        this.showSmartSuggestion({
          id: "exit_intent",
          title: "😊 Остались вопросы?",
          message: "Мы всегда на связи!",
          actions: [
            { text: "📞 Позвонить", url: "tel:+79375246888", icon: "fa-phone" },
            {
              text: "💬 Telegram",
              url: "https://t.me/techresourceru",
              icon: "fa-telegram",
            },
            {
              text: "✉️ Email",
              url: "mailto:info@tech-re.ru",
              icon: "fa-envelope",
            },
            {
              text: "📝 Задать вопрос",
              url: "/support/",
              icon: "fa-question-circle",
            },
          ],
          priority: "high",
        });
        exitShown = true;
        sessionStorage.setItem("exit_shown", "true");
      }
    });
  }
  trackFormAttempts() {
    const forms = document.querySelectorAll("form");
    forms.forEach((form) => {
      let attemptCount = 0;
      form.addEventListener("submit", (e) => {
        attemptCount++;
        setTimeout(() => {
          const successMsg = document.querySelector(
            ".message.success, .alert-success",
          );
          if (!successMsg && attemptCount === 1) {
            this.showSmartSuggestion({
              id: "form_failed",
              title: "❓ Проблема с отправкой?",
              message: "Можем помочь другим способом",
              actions: [
                {
                  text: "📧 Написать на почту",
                  url: "mailto:info@tech-re.ru",
                  icon: "fa-envelope",
                },
                {
                  text: "💬 Telegram",
                  url: "https://t.me/techresourceru",
                  icon: "fa-telegram",
                },
              ],
              priority: "high",
            });
          }
        }, 2000);
      });
    });
  }
  trackCartAbandonment() {
    if (
      window.location.pathname === "/cart/" &&
      this.userBehavior.cartItems > 0
    ) {
      let timer = setTimeout(() => {
        this.showSmartSuggestion({
          id: "cart_reminder",
          title: "🎁 Персональное предложение",
          message: "Оформите заказ сейчас и получите скидку 5%",
          actions: [
            {
              text: "✅ Оформить",
              url: "/cart/checkout/",
              icon: "fa-credit-card",
            },
            {
              text: "📄 Запросить КП",
              url: "/technical-task/",
              icon: "fa-file-invoice",
            },
            { text: "💬 Есть вопрос", url: "/contacts/", icon: "fa-headset" },
          ],
          priority: "high",
        });
      }, 30000);
      window.addEventListener("beforeunload", () => clearTimeout(timer));
    }
  }
  trackPriceFilter() {
    const priceInputs = document.querySelectorAll(
      'input[name*="price"], input[name*="min"], input[name*="max"]',
    );
    if (priceInputs.length === 0) return;
    let filterTimer;
    let filterCount = 0;
    priceInputs.forEach((input) => {
      input.addEventListener("change", () => {
        filterCount++;
        clearTimeout(filterTimer);
        filterTimer = setTimeout(() => {
          if (filterCount >= 2) {
            this.showSmartSuggestion({
              id: "price_help",
              title: "💰 Подбор по бюджету",
              message: "Поможем подобрать оптимальный вариант",
              actions: [
                {
                  text: "📊 Сортировка по цене",
                  url: "/products/?sort=price",
                  icon: "fa-sort-amount-down",
                },
                {
                  text: "📋 Запросить прайс",
                  url: "/technical-task/",
                  icon: "fa-file-excel",
                },
              ],
              priority: "low",
            });
            filterCount = 0;
          }
        }, 3000);
      });
    });
  }
  trackServicePageBehavior() {
    if (!window.location.pathname.includes("/services/")) return;
    const serviceCards = document.querySelectorAll(
      ".service-card, .service-item",
    );
    let serviceClicks = [];
    serviceCards.forEach((card) => {
      card.addEventListener("click", () => {
        const title = card.querySelector("h3, h4")?.textContent || "";
        serviceClicks.push(title);
        if (serviceClicks.length >= 2) {
          this.showSmartSuggestion({
            id: "service_combination",
            title: "🏗️ Комплекс услуг",
            message: "Закажите несколько услуг — получите скидку",
            actions: [
              {
                text: "📋 Запросить комплексное КП",
                url: "/technical-task/",
                icon: "fa-file-invoice",
              },
              {
                text: "📞 Позвонить инженеру",
                url: "tel:+79375246888",
                icon: "fa-phone",
              },
            ],
            priority: "medium",
          });
          serviceClicks = [];
        }
      });
    });
  }
  showSmartSuggestion(suggestion) {
    const lastShown = sessionStorage.getItem(`sugg_${suggestion.id}`);
    if (lastShown && Date.now() - parseInt(lastShown) < 180000) return;
    const currentHighPriority = sessionStorage.getItem("current_high_priority");
    if (
      suggestion.priority === "low" &&
      currentHighPriority &&
      Date.now() - parseInt(currentHighPriority) < 60000
    )
      return;
    this.createClickableSuggestion(suggestion);
    sessionStorage.setItem(`sugg_${suggestion.id}`, Date.now().toString());
    if (suggestion.priority === "high") {
      sessionStorage.setItem("current_high_priority", Date.now().toString());
    }
  }
  createClickableSuggestion(suggestion) {
    const old = document.querySelector(".assistant-smart-card");
    if (old) old.remove();
    const card = document.createElement("div");
    card.className = "assistant-smart-card";
    const actionsHtml = suggestion.actions
      .map(
        (action) =>
          `<button class="assistant-action"data-url="${action.url}"data-action="${action.action || ""}"><i class="fas ${action.icon}"></i><span>${action.text}</span></button>`,
      )
      .join("");
    card.innerHTML = `<div class="assistant-card-header"><div class="assistant-icon">💡</div><div class="assistant-title">${suggestion.title}</div><button class="assistant-close">✕</button></div><div class="assistant-message">${suggestion.message}</div><div class="assistant-actions">${actionsHtml}</div>`;
    this.addCardStyles();
    document.body.appendChild(card);
    card
      .querySelector(".assistant-close")
      .addEventListener("click", () => card.remove());
    card.querySelectorAll(".assistant-action").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const url = btn.dataset.url;
        const action = btn.dataset.action;
        if (action === "add_current_to_cart") {
          const addBtn = document.querySelector(
            ".add-to-cart, .btn-add-to-cart",
          );
          if (addBtn) addBtn.click();
          card.remove();
        } else if (action === "show_promo") {
          alert("Промокод: TECH2026 — скидка 5% на первый заказ");
          card.remove();
        } else if (url && url !== "#") {
          window.location.href = url;
        }
      });
    });
    setTimeout(() => {
      if (card.parentElement) card.remove();
    }, 15000);
  }
  addCardStyles() {
    if (document.querySelector("#assistant-styles")) return;
    const styles = document.createElement("style");
    styles.id = "assistant-styles";
    styles.textContent = `.assistant-smart-card{position:fixed;bottom:100px;right:20px;width:340px;background:white;border-radius:16px;box-shadow:0 10px 40px rgba(0,0,0,0.2);z-index:10001;overflow:hidden;animation:slideInRight 0.3s ease;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;border:1px solid#e5e5e5}@keyframes slideInRight{from{opacity:0;transform:translateX(100%)}to{opacity:1;transform:translateX(0)}}.assistant-card-header{display:flex;align-items:center;padding:15px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white}.assistant-icon{font-size:24px;margin-right:10px}.assistant-title{flex:1;font-weight:600;font-size:16px}.assistant-close{background:none;border:none;color:white;cursor:pointer;font-size:16px;opacity:0.7}.assistant-close:hover{opacity:1}.assistant-message{padding:15px;background:#f8f9fa;font-size:14px;color:#333;border-bottom:1px solid#e5e5e5}.assistant-actions{padding:12px;display:flex;flex-direction:column;gap:8px}.assistant-action{display:flex;align-items:center;gap:12px;padding:10px 12px;background:#f8f9fa;border:none;border-radius:10px;cursor:pointer;font-size:14px;color:#333;transition:all 0.2s;text-align:left}.assistant-action:hover{background:#e9ecef;transform:translateX(5px)}.assistant-action i{width:20px;color:#667eea}@media(max-width:768px){.assistant-smart-card{width:calc(100vw-40px);right:10px;bottom:80px}}`;
    document.head.appendChild(styles);
  }
  createFloatingButton() {
    const btn = document.createElement("div");
    btn.className = "assistant-floating-btn";
    btn.innerHTML =
      '<i class="fas fa-robot"></i><span class="assistant-pulse"></span>';
    btn.title = "Умный помощник";
    const btnStyles = document.createElement("style");
    btnStyles.textContent = `.assistant-floating-btn{position:fixed;bottom:20px;right:20px;width:56px;height:56px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;z-index:10000;box-shadow:0 4px 15px rgba(0,0,0,0.2);transition:transform 0.3s}.assistant-floating-btn:hover{transform:scale(1.1)}.assistant-floating-btn i{font-size:28px;color:white}.assistant-pulse{position:absolute;width:100%;height:100%;border-radius:50%;background:rgba(102,126,234,0.4);animation:pulse 2s infinite}@keyframes pulse{0%{transform:scale(1);opacity:1}100%{transform:scale(1.5);opacity:0}}`;
    document.head.appendChild(btnStyles);
    document.body.appendChild(btn);
    btn.addEventListener("click", () => {
      this.showSmartSuggestion({
        id: "manual_help",
        title: "🤖 Чем могу помочь?",
        message: "Выберите действие:",
        actions: [
          { text: "📞 Связаться с нами", url: "/contacts/", icon: "fa-phone" },
          {
            text: "📋 Заполнить ТЗ",
            url: "/technical-task/",
            icon: "fa-file-alt",
          },
          { text: "🛒 Перейти в каталог", url: "/products/", icon: "fa-box" },
          {
            text: "💬 Задать вопрос",
            url: "/support/",
            icon: "fa-question-circle",
          },
        ],
        priority: "high",
      });
    });
  }
  initHotkeys() {
    document.addEventListener("keydown", (e) => {
      if (e.ctrlKey && e.altKey && e.key === "h") {
        e.preventDefault();
        const btn = document.querySelector(".assistant-floating-btn");
        if (btn) btn.click();
      }
      if (e.ctrlKey && e.altKey && e.key === "c") {
        e.preventDefault();
        window.location.href = "/contacts/";
      }
      if (e.ctrlKey && e.altKey && e.key === "p") {
        e.preventDefault();
        window.location.href = "/products/";
      }
    });
    if (!sessionStorage.getItem("hotkeys_shown")) {
      setTimeout(() => {
        this.showSmartSuggestion({
          id: "hotkeys_tip",
          title: "⌨️ Горячие клавиши",
          message:
            "Ctrl+Alt+H — помощь, Ctrl+Alt+C — контакты, Ctrl+Alt+P — каталог",
          actions: [{ text: "🔧 Понятно", url: "#", icon: "fa-check" }],
          priority: "low",
        });
        sessionStorage.setItem("hotkeys_shown", "true");
      }, 30000);
    }
  }
}
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => new SmartAssistant());
} else {
  new SmartAssistant();
}
