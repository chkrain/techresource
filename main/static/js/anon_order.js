async function loadAnonymousCartItems() {
  console.log("🔄 Загружаем товары из анонимной корзины...");
  try {
    const t = await fetch("/anonymous-cart/items/", {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    console.log("📨 Ответ от сервера получен");
    const e = await t.json();
    if ((console.log("📊 Данные корзины:", e), e.success))
      renderCartItems(e.items, e.total);
    else {
      console.log("ℹ️ Корзина пуста или ошибка");
      const t = document.getElementById("anonymousCartItems");
      t &&
        (t.innerHTML =
          '\n                    <div class="empty-cart">\n                        <div class="empty-cart-icon">🛒</div>\n                        <h3>Корзина пуста</h3>\n                        <p>Добавьте товары из каталога, чтобы сделать заказ</p>\n                        <a href="{% url \'products\' %}" class="btn btn-primary" style="display: inline-block; margin-top: 1rem;">\n                            📦 Перейти к покупкам\n                        </a>\n                    </div>\n                ');
      const e = document.getElementById("itemsCount");
      e && (e.textContent = "0 товар(ов)");
    }
  } catch (t) {
    console.error("❌ Ошибка загрузки корзины:", t);
    const e = document.getElementById("anonymousCartItems");
    e &&
      (e.innerHTML =
        '\n                <div class="empty-cart">\n                    <div class="empty-cart-icon">⚠️</div>\n                    <h3>Ошибка загрузки</h3>\n                    <p>Попробуйте обновить страницу</p>\n                </div>\n            ');
  }
}
function renderCartItems(t, e) {
  if ((console.log("🛒 Рендерим товары:", t), 0 === t.length)) {
    document.getElementById("anonymousCartItems").innerHTML =
      '\n            <div class="empty-cart">\n                <div class="empty-cart-icon">🛒</div>\n                <h3>Корзина пуста</h3>\n                <p>Добавьте товары из каталога, чтобы сделать заказ</p>\n                <a href="{% url \'products\' %}" class="btn btn-primary" style="display: inline-block; margin-top: 1rem;">\n                    📦 Перейти к покупкам\n                </a>\n            </div>\n        ';
    const t = document.getElementById("itemsCount");
    return void (t && (t.textContent = "0 товар(ов)"));
  }
  const n = document.getElementById("itemsCount");
  n && (n.textContent = `${t.length} товар(ов)`);
  let o = "";
  (t.forEach((t) => {
    const e = parseFloat(t.total),
      n = parseFloat(t.price),
      s = t.max_quantity || 999;
    o += `\n            <div class="cart-item" data-product-id="${t.product_id}">\n                <div class="item-image">\n                    ${t.image ? `<img src="${t.image}" alt="${t.name}" loading="lazy">` : '\n                        <div class="image-placeholder">\n                            <span class="placeholder-icon">⚙️</span>\n                        </div>\n                    '}\n                </div>\n                \n                <div class="item-details">\n                    <h3 class="item-title">${t.name}</h3>\n                    ${t.article ? `<p class="item-article">Артикул: ${t.article}</p>` : ""}\n                    \n                    <div class="item-price-mobile">\n                        <span class="price">${n.toFixed(2)} ₽</span>\n                        <span class="total">Итого: <span class="mobile-total-price">${e.toFixed(2)}</span> ₽</span>\n                    </div>\n                </div>\n                \n                <div class="item-quantity">\n                    <div class="quantity-controls">\n                        <button class="quantity-btn decrease" type="button" onclick="updateQuantity(${t.product_id}, -1)" ${t.quantity <= 1 ? "disabled" : ""}>\n                            −\n                        </button>\n                        \n                        <input type="number" class="quantity-input" value="${t.quantity}" \n                               min="1" max="${s}" \n                               onchange="updateQuantity(${t.product_id}, 0, this.value)"\n                               data-price="${n}"\n                               data-max-quantity="${s}">\n                        \n                        <button class="quantity-btn increase" type="button" onclick="updateQuantity(${t.product_id}, 1)" ${t.quantity >= s ? "disabled" : ""}>\n                            +\n                        </button>\n                    </div>\n                </div>\n                \n                <div class="item-price">\n                    <div class="price-per-item">${n.toFixed(2)} ₽/шт</div>\n                    <div class="total-price">${e.toFixed(2)} ₽</div>\n                </div>\n                \n                <div class="item-remove">\n                    <button class="remove-btn" type="button" onclick="removeFromCart(${t.product_id})" title="Удалить из заказа">\n                        🗑️\n                    </button>\n                </div>\n            </div>\n        `;
  }),
    (o += `\n        <div class="summary-total">\n            <span>Итого к оплате:</span>\n            <span class="total-amount">${parseFloat(e).toFixed(2)} ₽</span>\n        </div>\n    `),
    (document.getElementById("anonymousCartItems").innerHTML = o));
}
async function updateQuantity(t, e, n = null) {
  try {
    const o = await fetch("/anonymous-cart/update/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ product_id: t, delta: e, quantity: n }),
      }),
      s = await o.json();
    s.success
      ? (loadAnonymousCartItems(),
        updateCartCounter(s.cart_count),
        showToast("Количество обновлено", "success"))
      : showToast(s.error || "Ошибка обновления", "error");
  } catch (t) {
    (console.error("Error updating quantity:", t),
      showToast("Ошибка соединения", "error"));
  }
}
async function removeFromCart(t) {
  if (confirm("Вы уверены, что хотите удалить товар из заказа?"))
    try {
      const e = await fetch("/anonymous-cart/remove/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
            "X-Requested-With": "XMLHttpRequest",
          },
          body: JSON.stringify({ product_id: t }),
        }),
        n = await e.json();
      n.success &&
        (loadAnonymousCartItems(),
        updateCartCounter(n.cart_count),
        showToast("Товар удален из заказа", "success"));
    } catch (t) {
      (console.error("Error removing item:", t),
        showToast("Ошибка соединения", "error"));
    }
}
function updateCartCounter(t) {
  const e = document.getElementById("anonymousCartCount");
  e &&
    ((e.textContent = t), (e.style.display = t > 0 ? "inline-block" : "none"));
}
function showToast(t, e = "success") {
  const n = document.createElement("div");
  ((n.className = `cart-message ${e}`),
    (n.style.cssText =
      "\n        position: fixed;\n        top: 20px;\n        right: 20px;\n        padding: 1rem 1.5rem;\n        border-radius: 12px;\n        color: white;\n        font-weight: 600;\n        z-index: 10000;\n        transform: translateX(400px);\n        transition: transform 0.3s ease;\n        max-width: 300px;\n    "),
    (n.style.background =
      "success" === e ? "#48bb78" : "error" === e ? "#e53e3e" : "#0052cc"),
    (n.textContent = t),
    document.body.appendChild(n),
    setTimeout(() => (n.style.transform = "translateX(0)"), 100),
    setTimeout(() => {
      ((n.style.transform = "translateX(400px)"),
        setTimeout(() => {
          n.parentNode && n.remove();
        }, 300));
    }, 3e3));
}
function getCSRFToken() {
  let t = null;
  const e = document.querySelector("[name=csrfmiddlewaretoken]");
  if ((e && (t = e.value), !t)) {
    const e = document.querySelector('meta[name="csrf-token"]');
    e && (t = e.getAttribute("content"));
  }
  if (!t) {
    const e = "csrftoken";
    if (document.cookie && "" !== document.cookie) {
      const n = document.cookie.split(";");
      for (let o = 0; o < n.length; o++) {
        const s = n[o].trim();
        if (s.substring(0, e.length + 1) === e + "=") {
          t = decodeURIComponent(s.substring(e.length + 1));
          break;
        }
      }
    }
  }
  return t;
}
(document.addEventListener("DOMContentLoaded", function () {
  const t = document.getElementById("fileInput"),
    e = document.querySelector(".file-upload-area"),
    n = document.getElementById("filePreview");
  function o() {
    if (t.files.length > 0) {
      const s = t.files[0];
      if (s.size > 10485760)
        return (
          alert("Файл слишком большой. Максимальный размер: 10 МБ"),
          void (t.value = "")
        );
      ((n.innerHTML = `\n                <div class="file-item">\n                    <div class="file-info">\n                        <div class="file-icon">${((o = s.name), { pdf: "📄", doc: "📝", docx: "📝", xls: "📊", xlsx: "📊", jpg: "🖼️", jpeg: "🖼️", png: "🖼️", zip: "🗜️", rar: "🗜️" }[o.split(".").pop().toLowerCase()] || "📎")}</div>\n                        <div class="file-details">\n                            <div class="file-name">${s.name}</div>\n                            <div class="file-size">${(function (
        t,
      ) {
        if (0 === t) return "0 Б";
        const e = Math.floor(Math.log(t) / Math.log(1024));
        return (
          parseFloat((t / Math.pow(1024, e)).toFixed(2)) +
          " " +
          ["Б", "КБ", "МБ", "ГБ"][e]
        );
      })(
        s.size,
      )}</div>\n                        </div>\n                    </div>\n                    <button type="button" class="file-remove" onclick="removeFile()">\n                        <i class="fas fa-times"></i>\n                    </button>\n                </div>\n            `),
        n.classList.add("show"),
        e.classList.remove("drag-over"));
    }
    var o;
  }
  (t.addEventListener("change", o),
    (window.removeFile = function () {
      ((t.value = ""), n.classList.remove("show"), (n.innerHTML = ""));
    }),
    ["dragenter", "dragover"].forEach((t) => {
      e.addEventListener(t, function (t) {
        (t.preventDefault(),
          t.stopPropagation(),
          this.classList.add("drag-over"));
      });
    }),
    ["dragleave", "drop"].forEach((t) => {
      e.addEventListener(t, function (t) {
        (t.preventDefault(),
          t.stopPropagation(),
          this.classList.remove("drag-over"));
      });
    }),
    e.addEventListener("drop", function (e) {
      const n = e.dataTransfer;
      ((t.files = n.files), o());
    }));
}),
  document
    .getElementById("anonymousOrderForm")
    .addEventListener("submit", async function (t) {
      t.preventDefault();
      const e = new FormData(this),
        n = this.querySelector('button[type="submit"]'),
        o = n.innerHTML,
        s = this.querySelectorAll("[required]");
      let a = !0;
      if (
        (s.forEach((t) => {
          t.value.trim()
            ? (t.style.borderColor = "#e9ecef")
            : ((t.style.borderColor = "#e53e3e"), (a = !1));
        }),
        a)
      ) {
        ((n.innerHTML = "⏳ Отправляем..."), (n.disabled = !0));
        try {
          const t = await fetch("/anonymous-cart/create-order/", {
              method: "POST",
              body: e,
              headers: { "X-Requested-With": "XMLHttpRequest" },
            }),
            s = await t.json();
          s.success
            ? (showToast(
                "✅ Заявка отправлена! Счет будет выставлен в течение рабочего дня.",
                "success",
              ),
              setTimeout(() => {
                window.location.href = "/";
              }, 2e3))
            : (showToast(s.error || "Ошибка отправки заявки", "error"),
              (n.innerHTML = o),
              (n.disabled = !1));
        } catch (t) {
          (console.error("Error submitting order:", t),
            showToast("Ошибка соединения", "error"),
            (n.innerHTML = o),
            (n.disabled = !1));
        }
      } else showToast("Заполните все обязательные поля", "error");
    }),
  document.addEventListener("DOMContentLoaded", function () {
    loadAnonymousCartItems();
  }));
