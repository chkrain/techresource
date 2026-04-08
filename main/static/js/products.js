let searchTimeout,
  currentPage = 1,
  isLoading = !1;
function initializeCategoryDropdown() {
  const categoryDropdownToggle = document.getElementById(
    "categoryDropdownToggle",
  );
  const categoryDropdown = document.getElementById("categoryDropdown");
  const categoryHiddenInput = document.getElementById("categoryHiddenInput");
  const selectedCategoryText = document.getElementById("selectedCategoryText");
  if (!categoryDropdownToggle || !categoryDropdown) return;
  categoryDropdownToggle.addEventListener("click", function (e) {
    e.stopPropagation();
    categoryDropdownToggle.classList.toggle("active");
    categoryDropdown.classList.toggle("show");
  });
  document.addEventListener("click", function (e) {
    if (
      !categoryDropdown.contains(e.target) &&
      !categoryDropdownToggle.contains(e.target)
    ) {
      categoryDropdownToggle.classList.remove("active");
      categoryDropdown.classList.remove("show");
    }
  });
  const expandButtons = categoryDropdown.querySelectorAll(
    ".expand-children-btn",
  );
  expandButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.stopPropagation();
      const categoryId = this.getAttribute("data-category-id");
      const childrenContainer = document.getElementById(
        `children-${categoryId}`,
      );
      if (childrenContainer) {
        const isExpanded = this.classList.contains("expanded");
        if (isExpanded) {
          childrenContainer.style.display = "none";
          this.classList.remove("expanded");
          this.querySelector(".expand-icon").textContent = "+";
        } else {
          childrenContainer.style.display = "block";
          this.classList.add("expanded");
          this.querySelector(".expand-icon").textContent = "−";
        }
      }
    });
  });
  const categoryRadios = categoryDropdown.querySelectorAll(".category-radio");
  categoryRadios.forEach((radio) => {
    radio.addEventListener("change", function () {
      const label = this.closest(".checkbox-label");
      const categoryName = label.querySelector(".category-name").textContent;
      if (selectedCategoryText) {
        selectedCategoryText.textContent = categoryName;
      }
      if (categoryHiddenInput) {
        categoryHiddenInput.value = this.value;
      }
      categoryDropdown
        .querySelectorAll(".category-option")
        .forEach((option) => {
          option.classList.remove("active");
        });
      this.closest(".category-option").classList.add("active");
      categoryDropdownToggle.classList.remove("active");
      categoryDropdown.classList.remove("show");
      loadProducts(1, { category: this.value });
    });
  });
  function expandToSelectedCategory() {
    const selectedRadio = categoryDropdown.querySelector(
      ".category-radio:checked",
    );
    if (!selectedRadio) return;
    selectedRadio.closest(".category-option").classList.add("active");
    let parentContainer = selectedRadio.closest(".children-container");
    while (parentContainer) {
      const parentId = parentContainer.id.replace("children-", "");
      const expandBtn = categoryDropdown.querySelector(
        `[data-category-id="${parentId}"]`,
      );
      if (expandBtn) {
        expandBtn.classList.add("expanded");
        expandBtn.querySelector(".expand-icon").textContent = "−";
        parentContainer.style.display = "block";
      }
      parentContainer = parentContainer.parentElement.closest(
        ".children-container",
      );
    }
  }
  expandToSelectedCategory();
}
function clearFilter(filterType) {
  if (filterType === "category") {
    const allCategoriesRadio = document.querySelector(
      'input[name="category"][value=""]',
    );
    if (allCategoriesRadio) {
      allCategoriesRadio.checked = true;
      allCategoriesRadio.dispatchEvent(new Event("change"));
    }
    const selectedCategoryText = document.getElementById(
      "selectedCategoryText",
    );
    if (selectedCategoryText) {
      selectedCategoryText.textContent = "Все категории";
    }
    const categoryHiddenInput = document.getElementById("categoryHiddenInput");
    if (categoryHiddenInput) {
      categoryHiddenInput.value = "";
    }
    const categoryDropdown = document.getElementById("categoryDropdown");
    if (categoryDropdown) {
      categoryDropdown
        .querySelectorAll(".category-option")
        .forEach((option) => {
          option.classList.remove("active");
        });
      const allOption = categoryDropdown.querySelector(
        '.category-option[data-category-value=""]',
      );
      if (allOption) allOption.classList.add("active");
    }
  } else if (filterType === "search") {
    const searchInput = document.getElementById("searchInput");
    if (searchInput) {
      searchInput.value = "";
    }
  } else if (filterType === "brand") {
    const brandSelect = document.querySelector('select[name="brand"]');
    if (brandSelect) {
      brandSelect.value = "";
    }
  } else if (filterType === "price") {
    const priceMin = document.getElementById("priceMin");
    const priceMax = document.getElementById("priceMax");
    if (priceMin) priceMin.value = "";
    if (priceMax) priceMax.value = "";
  } else if (filterType === "in_stock") {
    const inStockCheckbox = document.getElementById("inStockCheckbox");
    if (inStockCheckbox) {
      inStockCheckbox.checked = false;
    }
  }
  loadProducts(1, getCurrentFilters());
}
function getCurrentFilters() {
  const filters = {};
  const categoryHiddenInput = document.getElementById("categoryHiddenInput");
  if (categoryHiddenInput && categoryHiddenInput.value) {
    filters.category = categoryHiddenInput.value;
  }
  const searchInput = document.getElementById("searchInput");
  if (searchInput && searchInput.value.trim()) {
    filters.search = searchInput.value.trim();
  }
  const priceMin = document.getElementById("priceMin");
  const priceMax = document.getElementById("priceMax");
  if (priceMin && priceMin.value) filters.price_min = priceMin.value;
  if (priceMax && priceMax.value) filters.price_max = priceMax.value;
  const inStockCheckbox = document.getElementById("inStockCheckbox");
  if (inStockCheckbox && inStockCheckbox.checked) {
    filters.in_stock = "true";
  }
  const sortSelect = document.getElementById("sortSelect");
  if (sortSelect && sortSelect.value) {
    filters.sort_by = sortSelect.value;
  }
  return filters;
}
function updateURL(filters) {
  const url = new URL(window.location);
  url.search = "";
  Object.keys(filters).forEach((key) => {
    if (filters[key] || filters[key] === 0 || filters[key] === false) {
      url.searchParams.set(key, filters[key]);
    }
  });
  if (url.searchParams.get("page") === "1") {
    url.searchParams.delete("page");
  }
  window.history.replaceState({}, "", url);
}
function updateFilters() {
  const e = document.getElementById("filtersForm"),
    t = new FormData(e),
    n = {};
  for (let [e, o] of t.entries()) n[e] = o;
  (n.in_stock || (n.in_stock = ""),
    updateURL(n),
    updateActiveFilters(n),
    loadProducts(1, n));
}
function debouncedSearch() {
  const e = document.getElementById("searchInput");
  e &&
    (clearTimeout(searchTimeout),
    (searchTimeout = setTimeout(() => {
      const t = e.value,
        n = document.getElementById("filtersForm"),
        o = new FormData(n),
        a = {};
      for (let [e, t] of o.entries()) a[e] = t;
      ((a.search = t), updateURL(a), loadProducts(1, a));
    }, 500)));
}
async function loadProducts(page = 1, customFilters = {}) {
  if (isLoading) return;
  isLoading = true;
  currentPage = page;
  const loading = document.getElementById("loadingIndicator");
  const container = document.getElementById("productsContainer");
  const pagination = document.getElementById("paginationContainer");
  if (loading) loading.style.display = "block";
  if (page === 1 && container) {
    container.style.opacity = "0.5";
  }
  try {
    const filters = getCurrentFilters();
    Object.assign(filters, customFilters);
    Object.keys(filters).forEach((key) => {
      if (!filters[key] && filters[key] !== 0) {
        delete filters[key];
      }
    });
    filters.page = page;
    const params = new URLSearchParams(filters);
    const csrfToken = getCSRFToken();
    const headers = { "X-Requested-With": "XMLHttpRequest" };
    if (csrfToken) {
      headers["X-CSRFToken"] = csrfToken;
    }
    const response = await fetch(`?${params.toString()}`, {
      headers: headers,
      credentials: "include",
    });
    if (!response.ok) {
      if (response.redirected && response.url.includes("/login/")) {
        window.location.href =
          "/login/?next=" + encodeURIComponent(window.location.pathname);
        return;
      }
      throw new Error("Network error: " + response.status);
    }
    const data = await response.json();
    if (!data.success) {
      throw new Error("Failed to load products");
    }
    if (container) {
      container.innerHTML = data.products_html;
      container.style.opacity = "1";
    }
    const resultsCount = document.getElementById("resultsCount");
    if (resultsCount) {
      resultsCount.textContent = data.total_count;
    }
    if (pagination) {
      if (data.has_next) {
        pagination.innerHTML = `${page > 1 ? `<a href="#"class="pagination-btn"data-page="${page - 1}">←Назад</a>` : "<span></span>"}<span class="pagination-info">Страница <span id="currentPage">${page}</span> из <span id="totalPages">${data.total_pages}</span></span><a href="#"class="pagination-btn"data-page="${data.next_page_number}">Далее→</a>`;
        pagination.style.display = "flex";
      } else {
        pagination.innerHTML = `${page > 1 ? `<a href="#"class="pagination-btn"data-page="${page - 1}">←Назад</a>` : "<span></span>"}<span class="pagination-info">Страница <span id="currentPage">${page}</span> из <span id="totalPages">${data.total_pages}</span></span><span class="pagination-info">Показаны все товары</span>`;
        pagination.style.display = "flex";
      }
      pagination.querySelectorAll(".pagination-btn").forEach((btn) => {
        btn.addEventListener("click", function (e) {
          e.preventDefault();
          const pageNum = parseInt(this.getAttribute("data-page"));
          if (!isNaN(pageNum)) {
            loadProducts(pageNum);
          }
        });
      });
    }
    updateActiveFilters(filters);
    delete filters.page;
    updateURL(filters);
    initializeProductHandlers();
  } catch (error) {
    console.error("Error loading products:", error);
    if (error.message.includes("401") || error.message.includes("403")) {
      window.location.href =
        "/login/?next=" + encodeURIComponent(window.location.pathname);
    } else {
      showToast("Ошибка при загрузке товаров", "error");
    }
  } finally {
    isLoading = false;
    if (loading) loading.style.display = "none";
    if (container) container.style.opacity = "1";
  }
}
function loadPage(e, t) {
  (t && t.preventDefault(), loadProducts(e));
}
function clearAllFilters() {
  document
    .getElementById("filtersForm")
    .querySelectorAll("input, select")
    .forEach((e) => {
      "checkbox" === e.type
        ? (e.checked = !1)
        : "text" === e.type || "number" === e.type
          ? (e.value = "")
          : "SELECT" === e.tagName && (e.selectedIndex = 0);
    });
  const e = document.getElementById("searchInput");
  (e && (e.value = ""), updateURL({}), loadProducts(1, {}));
}
function removeFilter(e) {
  const t = document.getElementById("filtersForm");
  if ("search" === e) {
    const e = document.getElementById("searchInput");
    e && (e.value = "");
    const n = t.querySelector('input[name="search"]');
    n && (n.value = "");
  } else if ("in_stock" === e) {
    const e = t.querySelector('input[name="in_stock"]');
    e && (e.checked = !1);
  } else if ("price" === e) {
    const e = t.querySelector('input[name="price_min"]'),
      n = t.querySelector('input[name="price_max"]');
    (e && (e.value = ""), n && (n.value = ""));
  } else {
    const n = t.querySelector(`select[name="${e}"]`);
    n && (n.selectedIndex = 0);
  }
  updateFilters();
}
function initializeProductHandlers() {
  (document.querySelectorAll(".add-to-cart-btn").forEach((e) => {
    e.addEventListener("click", handleAddToCart);
  }),
    document.querySelectorAll(".wishlist-btn").forEach((e) => {
      "BUTTON" === e.tagName &&
        e.addEventListener("click", handleWishlistToggle);
    }),
    document.querySelectorAll(".view-btn").forEach((e) => {
      e.addEventListener("click", function () {
        const e = this.getAttribute("data-view");
        (document
          .querySelectorAll(".view-btn")
          .forEach((e) => e.classList.remove("active")),
          this.classList.add("active"));
        const t = document.querySelector(".products-grid");
        t &&
          ("list" === e
            ? t.classList.add("list-view")
            : t.classList.remove("list-view"));
      });
    }),
    document.querySelectorAll(".pagination-btn").forEach((e) => {
      e.addEventListener("click", function (e) {
        e.preventDefault();
        const t = this.getAttribute("data-page");
        t && loadPage(parseInt(t), e);
      });
    }),
    document.querySelectorAll(".active-filter button").forEach((e) => {
      e.addEventListener("click", function () {
        removeFilter(this.getAttribute("data-filter"));
      });
    }));
}
async function handleAddToCart(e) {
  e.preventDefault();
  const t = this.getAttribute("data-product-id"),
    n = this.innerHTML;
  ((this.innerHTML = "⏳ Добавляем..."),
    (this.disabled = !0),
    this.classList.add("loading"));
  try {
    const e = new FormData(),
      o = getCSRFToken();
    o && e.append("csrfmiddlewaretoken", o);
    const a = await fetch(`/cart/add/${t}/`, {
      method: "POST",
      headers: { "X-Requested-With": "XMLHttpRequest" },
      body: e,
      credentials: "same-origin",
    });
    if (!a.ok) throw new Error("Network error");
    const s = await a.json();
    if (!s.success)
      throw new Error(s.error || "Ошибка при добавлении в корзину");
    (showToast(
      s.message ||
        'Товар добавлен в <a href="/cart/" style="color: #fff; text-decoration: underline; font-weight: bold;">корзину</a>!',
      "success",
    ),
      updateCartCounter(s.cart_count),
      (this.innerHTML = "✅ Добавлено!"),
      setTimeout(() => {
        ((this.innerHTML = n),
          (this.disabled = !1),
          this.classList.remove("loading"));
      }, 1500));
  } catch (e) {
    (console.error("Error:", e),
      showToast(e.message || "Ошибка при добавлении в корзину", "error"),
      (this.innerHTML = n),
      (this.disabled = !1),
      this.classList.remove("loading"));
  }
}
async function handleWishlistToggle(e) {
  e.preventDefault();
  const t = this.getAttribute("data-product-id"),
    n =
      (this.classList.contains("in-wishlist"),
      this.querySelector(".wishlist-icon"));
  try {
    const e = new FormData(),
      o = getCSRFToken();
    o && e.append("csrfmiddlewaretoken", o);
    const a = await fetch(`/wishlist/toggle/${t}/`, {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest" },
        body: e,
        credentials: "same-origin",
      }),
      s = await a.json();
    if (!s.success) throw new Error(s.error);
    (showToast(s.message, "success"),
      updateWishlistCounter(s.wishlist_count),
      "added" === s.action
        ? (this.classList.add("in-wishlist"),
          n && (n.textContent = "❤️"),
          this.setAttribute("title", "Удалить из избранного"))
        : (this.classList.remove("in-wishlist"),
          n && (n.textContent = "🤍"),
          this.setAttribute("title", "Добавить в избранное")),
      n &&
        ((n.style.transform = "scale(1.3)"),
        setTimeout(() => {
          n.style.transform = "scale(1)";
        }, 300)));
  } catch (e) {
    (console.error("Error:", e),
      showToast(e.message || "Ошибка при работе с избранным", "error"));
  }
}
function showToast(e, t = "success") {
  const n = document.getElementById("toast-container");
  if (!n) return;
  const o = document.createElement("div");
  ((o.className = `toast ${t}`),
    (o.innerHTML = `\n<span class="toast-icon">${"success" === t ? "✅" : "❌"}</span>\n        <span class="toast-message">${e}</span>\n`),
    n.appendChild(o),
    setTimeout(() => o.classList.add("show"), 100),
    setTimeout(() => {
      (o.classList.remove("show"),
        setTimeout(() => {
          o.parentNode && o.parentNode.removeChild(o);
        }, 300));
    }, 3e3));
}
function updateWishlistCounter(e) {
  console.log("Wishlist count updated:", e);
}
function updateCartCounter(e) {
  console.log("Cart count updated:", e);
}
function getCSRFToken() {
  let e = null;
  const t = document.querySelector("[name=csrfmiddlewaretoken]");
  if ((t && (e = t.value), !e)) {
    const t = document.querySelector('meta[name="csrf-token"]');
    t && (e = t.getAttribute("content"));
  }
  if (!e) {
    const t = "csrftoken";
    if (document.cookie && "" !== document.cookie) {
      const n = document.cookie.split(";");
      for (let o = 0; o < n.length; o++) {
        const a = n[o].trim();
        if (a.substring(0, t.length + 1) === t + "=") {
          e = decodeURIComponent(a.substring(t.length + 1));
          break;
        }
      }
    }
  }
  return e;
}
async function updatePriceRange() {
  const e = document.querySelector('select[name="category"]')?.value || "",
    t = document.querySelector('select[name="brand"]')?.value || "";
  try {
    const n = await fetch(
        `/api/price-range/?category=${encodeURIComponent(e)}&brand=${encodeURIComponent(t)}`,
      ),
      o = await n.json(),
      a = document.querySelector(".price-range-info");
    a && (a.textContent = `Диапазон:${o.min_price}-${o.max_price}₽`);
  } catch (e) {
    console.error("Error updating price range:", e);
  }
}
function updateActiveFilters(filters = null) {
  const activeFiltersContainer = document.getElementById("activeFilters");
  if (!activeFiltersContainer) return;
  if (!filters) {
    filters = getCurrentFilters();
  }
  let filtersHtml = "";
  if (filters.search) {
    filtersHtml += `<span class="active-filter">Поиск:"${filters.search}"<button type="button"onclick="clearFilter('search')"data-filter="search">×</button></span>`;
  }
  if (filters.category) {
    let categoryName = filters.category;
    const categoryRadio = document.querySelector(
      `input[name="category"][value="${filters.category}"]`,
    );
    if (categoryRadio) {
      const label = categoryRadio.closest(".checkbox-label");
      if (label) {
        categoryName = label.querySelector(".category-name").textContent;
      }
    }
    filtersHtml += `<span class="active-filter">Категория:${categoryName}<button type="button"onclick="clearFilter('category')"data-filter="category">×</button></span>`;
  }
  if (filters.price_min || filters.price_max) {
    const min = filters.price_min || "0";
    const max = filters.price_max || "∞";
    filtersHtml += `<span class="active-filter">Цена:${min}-${max}₽<button type="button"onclick="clearFilter('price')"data-filter="price">×</button></span>`;
  }
  if (filters.in_stock === "true") {
    filtersHtml += `<span class="active-filter">Тольковналичии<button type="button"onclick="clearFilter('in_stock')"data-filter="in_stock">×</button></span>`;
  }
  activeFiltersContainer.innerHTML = filtersHtml;
  activeFiltersContainer
    .querySelectorAll(".active-filter button")
    .forEach((button) => {
      button.addEventListener("click", function () {
        const filterType = this.getAttribute("data-filter");
        clearFilter(filterType);
      });
    });
}
document.addEventListener("DOMContentLoaded", function () {
  initializeCategoryDropdown();
  initializeProductHandlers();
  updateActiveFilters();
  const searchInput = document.getElementById("searchInput");
  let searchTimeout;
  if (searchInput) {
    searchInput.addEventListener("input", function () {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        loadProducts(1, { search: this.value.trim() });
      }, 500);
    });
  }
  const inStockCheckbox = document.getElementById("inStockCheckbox");
  if (inStockCheckbox) {
    inStockCheckbox.addEventListener("change", function () {
      loadProducts(1, { in_stock: this.checked ? "true" : "" });
    });
  }
  const priceMin = document.getElementById("priceMin");
  const priceMax = document.getElementById("priceMax");
  let priceTimeout;
  function handlePriceChange() {
    clearTimeout(priceTimeout);
    priceTimeout = setTimeout(() => {
      const filters = {};
      if (priceMin && priceMin.value) filters.price_min = priceMin.value;
      if (priceMax && priceMax.value) filters.price_max = priceMax.value;
      loadProducts(1, filters);
    }, 500);
  }
  if (priceMin) priceMin.addEventListener("input", handlePriceChange);
  if (priceMax) priceMax.addEventListener("input", handlePriceChange);
  const sortSelect = document.getElementById("sortSelect");
  if (sortSelect) {
    sortSelect.addEventListener("change", function () {
      loadProducts(1, { sort_by: this.value });
    });
  }
  const clearFiltersBtn = document.getElementById("clearFiltersBtn");
  if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener("click", function () {
      clearFilter("category");
      clearFilter("search");
      clearFilter("price");
      clearFilter("in_stock");
      const brandSelect = document.querySelector('select[name="brand"]');
      if (brandSelect) brandSelect.value = "";
      if (sortSelect) sortSelect.value = "name";
      loadProducts(1, {});
    });
  }
});
