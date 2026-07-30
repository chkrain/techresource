function toggleMenu() {
    const nav = document.getElementById('main-nav');
    const btn = document.getElementById('mobileMenuBtn');
    
    nav.classList.toggle('active');
    btn.classList.toggle('active');
}
function updateCartUI(t) {
  if (t && void 0 !== t.cart_count) {
    const e = document.getElementById("anonymousCartCount");
    if (e) {
      t.cart_count > 0
        ? ((e.style.display = "inline-block"),
          (e.innerHTML = ""),
          e.classList.add("pulse"),
          setTimeout(() => e.classList.remove("pulse"), 500))
        : (e.style.display = "none");
    }
  }
}
function refreshCartCount() {
  fetch("/anonymous-cart/items/", {
    method: "GET",
    headers: { "X-Requested-With": "XMLHttpRequest" },
  })
    .then((t) => t.json())
    .then((t) => {
      t.success && updateCartUI({ cart_count: t.count });
    })
    .catch((t) => console.error("Error refreshing cart:", t));
}
function triggerCartUpdate(t) {
  document.dispatchEvent(new CustomEvent("cartUpdated", { detail: t }));
}
(AOS.init({ duration: 800, once: !0, offset: 100 }),
  document.addEventListener("click", function (t) {
    const e = document.getElementById("main-nav"),
      n = document.querySelector(".mobile-menu-btn");
    e.contains(t.target) ||
      n.contains(t.target) ||
      e.classList.remove("active");
  }),
  window.addEventListener("scroll", function () {
    const t = document.getElementById("header"),
      e = document.getElementById("backToTop");
    window.scrollY > 100
      ? (t.classList.add("scrolled"), e.classList.add("visible"))
      : (t.classList.remove("scrolled"), e.classList.remove("visible"));
  }),
  document.getElementById("backToTop").addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }),
  document.addEventListener("DOMContentLoaded", function () {
    const t = window.location.pathname;
    (document.querySelectorAll(".nav-link").forEach((e) => {
      e.getAttribute("href") === t && e.classList.add("active");
    }),
      (document.getElementById("currentYear").textContent =
        new Date().getFullYear()));
  }),
  document.querySelectorAll('a[href^="#"]').forEach((t) => {
    t.addEventListener("click", function (t) {
      t.preventDefault();
      const e = document.querySelector(this.getAttribute("href"));
      e && e.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }),
  document.querySelectorAll(".btn").forEach((t) => {
    t.addEventListener("click", function (t) {
      ("#" !== this.getAttribute("href") && "submit" !== this.type) ||
        ((this.style.transform = "scale(0.95)"),
        setTimeout(() => {
          this.style.transform = "";
        }, 150));
    });
  }),
  document.addEventListener("DOMContentLoaded", function () {
    (refreshCartCount(),
      document.addEventListener("cartUpdated", function (t) {
        updateCartUI(t.detail);
      }));
  }));
