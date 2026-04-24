class SmartAssistant {
  constructor() {
    this.userBehavior = {
      startTime: Date.now(),
      currentPage: window.location.pathname,
      searchAttempts: 0,
      productViews: [],
      scrollDepth: 0,
      formAttempts: 0,
      lastActivity: Date.now(),
      pageLoadTime: performance.now(),
    };
    this.suggestions = {
      product_search: [
        "Не нашли нужный товар? Напишите на info@tech-re.ru - подберем аналог",
        "Для подбора оборудования отправьте ТЗ на info@tech-re.ru",
        "Уточните наличие по телефону: 8 (937) 524-68-88",
      ],
      technical_help: [
        "Нужна помощь с выбором? Наши инженеры проконсультируют - info@tech-re.ru",
        "Сомневаетесь в характеристиках? Запросите техдокументацию",
        "Требуется доработка под вашу задачу? Обсудим! info@tech-re.ru",
      ],
      ordering: [
        "Нужен счет? Оформите заказ - вышлем в течение часа",
        "Для юрлиц доступна оплата по счету",
      ],
      general: [
        "Остались вопросы? info@tech-re.ru или 8 (937) 524-68-88",
        "Нужна консультация инженера? Позвоните: 8 (937) 524-68-88",
      ],
      slow_user: [
        "Видим, что вы изучаете сайт. Если нужна помощь - напишите нам",
        "Подбор оборудования - наша специализация. Обращайтесь!",
      ],
    };
    this.init();
  }
  init() {
    this.trackSearch();
    this.trackProductViews();
    this.trackScroll();
    this.trackTimeOnPage();
    this.trackInactivity();
    this.trackExitIntent();
    this.trackFormAttempts();
    this.trackProductListReturns();
    this.trackSlowNavigation();
  }
  trackSearch() {
    const searchInput = document.querySelector(
      'input[name="search"], input[type="search"]',
    );
    if (!searchInput) return;
    let searchTimer;
    searchInput.addEventListener("input", (e) => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        if (e.target.value.length > 2) {
          this.userBehavior.searchAttempts++;
          if (this.userBehavior.searchAttempts >= 2) {
            this.showSuggestion("product_search");
          }
        }
      }, 800);
    });
  }
  trackProductViews() {
    const originalPushState = history.pushState;
    history.pushState = function () {
      originalPushState.apply(this, arguments);
      setTimeout(() => this.checkProductPage(), 100);
    }.bind(this);
    window.addEventListener("popstate", () => {
      setTimeout(() => this.checkProductPage(), 100);
    });
    this.checkProductPage();
  }
  checkProductPage() {
    if (window.location.pathname.includes("/product/")) {
      const productId = window.location.pathname.split("/").pop();
      if (!this.userBehavior.productViews.includes(productId)) {
        this.userBehavior.productViews.push(productId);
        if (this.userBehavior.productViews.length >= 3) {
          this.showSuggestion("technical_help");
        }
      }
    }
  }
  trackScroll() {
    let scrollTimer;
    let maxScroll = 0;
    let scrollTriggered = false;
    window.addEventListener("scroll", () => {
      clearTimeout(scrollTimer);
      scrollTimer = setTimeout(() => {
        const scrollPercent =
          (window.scrollY /
            (document.documentElement.scrollHeight - window.innerHeight)) *
          100;
        if (scrollPercent > maxScroll) {
          maxScroll = scrollPercent;
          this.userBehavior.scrollDepth = maxScroll;
        }
        if (
          !scrollTriggered &&
          maxScroll > 70 &&
          window.location.pathname.includes("/services/")
        ) {
          this.showSuggestion("technical_help");
          scrollTriggered = true;
        }
        if (!scrollTriggered && maxScroll > 90) {
          this.showSuggestion("general");
          scrollTriggered = true;
        }
      }, 300);
    });
  }
  trackTimeOnPage() {
    let pageTimer = setInterval(() => {
      const timeOnPage = (Date.now() - this.userBehavior.startTime) / 1000;
      if (window.location.pathname.includes("/product/") && timeOnPage > 45) {
        this.showSuggestion("technical_help");
        clearInterval(pageTimer);
      }
      if (window.location.pathname.includes("/services/") && timeOnPage > 60) {
        this.showSuggestion("technical_help");
        clearInterval(pageTimer);
      }
      if (window.location.pathname.includes("/cart/") && timeOnPage > 90) {
        this.showSuggestion("ordering");
        clearInterval(pageTimer);
      }
      if (
        timeOnPage > 180 &&
        this.userBehavior.productViews.length === 0 &&
        this.userBehavior.searchAttempts === 0
      ) {
        this.showSuggestion("slow_user");
        clearInterval(pageTimer);
      }
    }, 30000);
  }
  trackInactivity() {
    let inactivityTimer;
    let inactivityShown = false;
    const resetInactivity = () => {
      clearTimeout(inactivityTimer);
      inactivityTimer = setTimeout(() => {
        if (!inactivityShown) {
          this.showSuggestion("general");
          inactivityShown = true;
        }
      }, 90000);
    };
    window.addEventListener("mousemove", resetInactivity);
    window.addEventListener("keypress", resetInactivity);
    window.addEventListener("click", resetInactivity);
    resetInactivity();
  }
  trackExitIntent() {
    document.addEventListener("mouseleave", (e) => {
      if (e.clientY < 0) {
        this.showSuggestion("general");
      }
    });
  }
  trackFormAttempts() {
    const forms = document.querySelectorAll("form");
    forms.forEach((form) => {
      let attemptCount = 0;
      form.addEventListener("submit", () => {
        setTimeout(() => {
          if (document.querySelector(".message.success")) return;
          attemptCount++;
          if (attemptCount >= 1) {
            this.showSuggestion("general");
          }
        }, 1500);
      });
    });
  }
  trackProductListReturns() {
    let returnCount = 0;
    let lastVisit = null;
    const checkReturn = () => {
      if (
        window.location.pathname === "/products/" &&
        this.userBehavior.productViews.length > 0
      ) {
        const now = Date.now();
        if (lastVisit && now - lastVisit < 180000) {
          returnCount++;
          if (returnCount >= 1) {
            this.showSuggestion("product_search");
            returnCount = 0;
          }
        }
        lastVisit = now;
      }
    };
    setInterval(checkReturn, 2000);
  }
  trackSlowNavigation() {
    if (this.userBehavior.pageLoadTime > 3000) {
      setTimeout(() => {
        this.showSuggestion("general");
      }, 5000);
    }
  }
  showSuggestion(category) {
    const lastSuggestion = sessionStorage.getItem("last_suggestion_time");
    if (lastSuggestion && Date.now() - parseInt(lastSuggestion) < 180000) {
      return;
    }
    const suggestions = this.suggestions[category];
    if (!suggestions || suggestions.length === 0) return;
    const randomSuggestion =
      suggestions[Math.floor(Math.random() * suggestions.length)];
    this.createAssistantBubble(randomSuggestion);
    sessionStorage.setItem("last_suggestion_time", Date.now().toString());
  }
  createAssistantBubble(message) {
    const oldBubble = document.querySelector(".assistant-bubble");
    if (oldBubble) oldBubble.remove();
    const bubble = document.createElement("div");
    bubble.className = "assistant-bubble";
    bubble.innerHTML = `<div class="assistant-message"><p>💡${message}</p><div class="assistant-actions"><button class="assistant-close">✕</button></div></div>`;
    const style = document.createElement("style");
    style.textContent = `.assistant-bubble{position:fixed;bottom:20px;right:20px;max-width:350px;background:#2d3748;color:white;border-radius:4px;box-shadow:0 10px 25px rgba(0,0,0,0.2);z-index:10000;animation:slideInRight 0.3s ease;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}.assistant-message{padding:14px 18px;display:flex;align-items:center;justify-content:space-between;gap:15px}.assistant-message p{margin:0;font-size:14px;line-height:1.4;flex:1}.assistant-actions{flex-shrink:0}.assistant-close{background:none;border:none;color:#9ca3af;cursor:pointer;padding:4px 8px;border-radius:4px;font-size:16px;transition:all 0.2s}.assistant-close:hover{color:white;background:rgba(255,255,255,0.1)}@keyframes slideInRight{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}@keyframes slideOutRight{from{transform:translateX(0);opacity:1}to{transform:translateX(100%);opacity:0}}`;
    document.head.appendChild(style);
    document.body.appendChild(bubble);
    bubble.querySelector(".assistant-close").onclick = () => {
      bubble.style.animation = "slideOutRight 0.3s ease";
      setTimeout(() => bubble.remove(), 300);
    };
    setTimeout(() => {
      if (bubble && bubble.parentElement) {
        bubble.style.animation = "slideOutRight 0.3s ease";
        setTimeout(() => bubble.remove(), 300);
      }
    }, 12000);
  }
}
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => new SmartAssistant());
} else {
  new SmartAssistant();
}
