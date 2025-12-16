let currentPage = 1;
let isLoading = false;
let searchTimeout;

function updateURL(params) {
    const url = new URL(window.location);
    Object.keys(params).forEach(key => {
        if (params[key]) {
            url.searchParams.set(key, params[key]);
        } else {
            url.searchParams.delete(key);
        }
    });
    url.searchParams.delete('page'); 
    window.history.replaceState({}, '', url);
}

function updateFilters() {
    const form = document.getElementById('filtersForm');
    const formData = new FormData(form);
    const params = {};
    
    for (let [key, value] of formData.entries()) {
        params[key] = value;
    }
    
    if (!params.in_stock) {
        params.in_stock = '';
    }
    
    updateURL(params);
    
    updateActiveFilters(params);
    
    loadProducts(1, params);
}

function updateActiveFilters(params) {
    const activeFiltersContainer = document.getElementById('activeFilters');
    if (!activeFiltersContainer) return;
    
    let activeFiltersHTML = '';
    
    // Поиск
    if (params.search) {
        activeFiltersHTML += `
            <span class="active-filter">
                Поиск: "${params.search}"
                <button type="button" data-filter="search">×</button>
            </span>
        `;
    }
    
    // Категория
    if (params.category) {
        activeFiltersHTML += `
            <span class="active-filter">
                Категория: ${params.category}
                <button type="button" data-filter="category">×</button>
            </span>
        `;
    }
    
    // Бренд
    if (params.brand) {
        activeFiltersHTML += `
            <span class="active-filter">
                Бренд: ${params.brand}
                <button type="button" data-filter="brand">×</button>
            </span>
        `;
    }
    
    // Цена
    if (params.price_min || params.price_max) {
        activeFiltersHTML += `
            <span class="active-filter">
                Цена: ${params.price_min || 0} - ${params.price_max || '∞'} ₽
                <button type="button" data-filter="price">×</button>
            </span>
        `;
    }
    
    if (params.in_stock === 'true') {
        activeFiltersHTML += `
            <span class="active-filter">
                Только в наличии
                <button type="button" data-filter="in_stock">×</button>
            </span>
        `;
    }
    
    activeFiltersContainer.innerHTML = activeFiltersHTML;
    
    document.querySelectorAll('.active-filter button').forEach(btn => {
        btn.addEventListener('click', function() {
            const filterName = this.getAttribute('data-filter');
            removeFilter(filterName);
        });
    });
}

function debouncedSearch() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;
    
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        const searchValue = searchInput.value;
        const form = document.getElementById('filtersForm');
        const formData = new FormData(form);
        const params = {};
        
        for (let [key, value] of formData.entries()) {
            params[key] = value;
        }
        params.search = searchValue;
        
        updateURL(params);
        loadProducts(1, params);
    }, 500);
}

async function loadProducts(page = 1, additionalParams = {}) {
    if (isLoading) return;
    
    isLoading = true;
    currentPage = page;
    
    const loadingIndicator = document.getElementById('loadingIndicator');
    const productsContainer = document.getElementById('productsContainer');
    const paginationContainer = document.getElementById('paginationContainer');
    
    if (loadingIndicator) {
        loadingIndicator.style.display = 'block';
    }
    if (page === 1 && productsContainer) {
        productsContainer.style.opacity = '0.5';
    }
    
    try {
        const form = document.getElementById('filtersForm');
        const formData = new FormData(form);
        const params = new URLSearchParams();
        
        for (let [key, value] of formData.entries()) {
            if (value) params.append(key, value);
        }
        
        Object.keys(additionalParams).forEach(key => {
            if (additionalParams[key]) {
                params.append(key, additionalParams[key]);
            }
        });
        
        params.append('page', page);
        
        const csrfToken = getCSRFToken();
        const headers = {
            'X-Requested-With': 'XMLHttpRequest',
        };
        
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }
        
        const response = await fetch(`?${params.toString()}`, {
            headers: headers,
            credentials: 'include'
        });
        
        if (!response.ok) {
            if (response.redirected && response.url.includes('/login/')) {
                window.location.href = '/login/?next=' + encodeURIComponent(window.location.pathname);
                return;
            }
            throw new Error('Network error: ' + response.status);
        }
        
        const data = await response.json();
        
        if (data.success) {
            if (productsContainer) {
                productsContainer.innerHTML = data.products_html;
            }
            
            const resultsCount = document.getElementById('resultsCount');
            if (resultsCount) {
                resultsCount.textContent = data.total_count;
            }
            
            if (paginationContainer && data.has_next) {
                paginationContainer.innerHTML = `
                    ${page > 1 ? `<a href="#" class="pagination-btn" data-page="${page - 1}">← Назад</a>` : '<span></span>'}
                    <span class="pagination-info">
                        Страница <span id="currentPage">${page}</span> из <span id="totalPages">${data.total_pages}</span>
                    </span>
                    <a href="#" class="pagination-btn" data-page="${data.next_page_number}">Далее →</a>
                `;
            } else if (paginationContainer) {
                paginationContainer.innerHTML = `
                    ${page > 1 ? `<a href="#" class="pagination-btn" data-page="${page - 1}">← Назад</a>` : '<span></span>'}
                    <span class="pagination-info">
                        Страница <span id="currentPage">${page}</span> из <span id="totalPages">${data.total_pages}</span>
                    </span>
                    <span class="pagination-info">Показаны все товары</span>
                `;
            }
            
            initializeProductHandlers();
            
        } else {
            throw new Error('Failed to load products');
        }
        
    } catch (error) {
        console.error('Error loading products:', error);
        
        if (error.message.includes('401') || error.message.includes('403')) {
            window.location.href = '/login/?next=' + encodeURIComponent(window.location.pathname);
        } else {
            showToast('Ошибка при загрузке товаров', 'error');
        }
    } finally {
        isLoading = false;
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
        if (productsContainer) {
            productsContainer.style.opacity = '1';
        }
    }
}

function loadPage(page, event) {
    if (event) event.preventDefault();
    loadProducts(page);
}

function clearAllFilters() {
    const form = document.getElementById('filtersForm');
    const inputs = form.querySelectorAll('input, select');
    
    inputs.forEach(input => {
        if (input.type === 'checkbox') {
            input.checked = false;
        } else if (input.type === 'text' || input.type === 'number') {
            input.value = '';
        } else if (input.tagName === 'SELECT') {
            input.selectedIndex = 0;
        }
    });
    
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.value = '';
    }
    
    updateURL({});
    
    loadProducts(1, {});
}

function removeFilter(filterName) {
    const form = document.getElementById('filtersForm');
    
    if (filterName === 'search') {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) searchInput.value = '';
        const hiddenSearch = form.querySelector('input[name="search"]');
        if (hiddenSearch) hiddenSearch.value = '';
    } else if (filterName === 'in_stock') {
        const checkbox = form.querySelector('input[name="in_stock"]');
        if (checkbox) checkbox.checked = false;
    } else if (filterName === 'price') {
        const priceMin = form.querySelector('input[name="price_min"]');
        const priceMax = form.querySelector('input[name="price_max"]');
        if (priceMin) priceMin.value = '';
        if (priceMax) priceMax.value = '';
    } else {
        const select = form.querySelector(`select[name="${filterName}"]`);
        if (select) select.selectedIndex = 0;
    }
    
    updateFilters();
}

function initializeProductHandlers() {
    document.querySelectorAll('.add-to-cart-btn').forEach(btn => {
        btn.addEventListener('click', handleAddToCart);
    });
    
    document.querySelectorAll('.wishlist-btn').forEach(btn => {
        if (btn.tagName === 'BUTTON') {
            btn.addEventListener('click', handleWishlistToggle);
        }
    });
    
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const view = this.getAttribute('data-view');
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            const productsGrid = document.querySelector('.products-grid');
            if (productsGrid) {
                if (view === 'list') {
                    productsGrid.classList.add('list-view');
                } else {
                    productsGrid.classList.remove('list-view');
                }
            }
        });
    });
    
    document.querySelectorAll('.pagination-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.getAttribute('data-page');
            if (page) {
                loadPage(parseInt(page), e);
            }
        });
    });
    
    document.querySelectorAll('.active-filter button').forEach(btn => {
        btn.addEventListener('click', function() {
            const filterName = this.getAttribute('data-filter');
            removeFilter(filterName);
        });
    });
}

async function handleAddToCart(e) {
    e.preventDefault();
    const productId = this.getAttribute('data-product-id');
    const originalText = this.innerHTML;
    
    this.innerHTML = '⏳ Добавляем...';
    this.disabled = true;
    this.classList.add('loading');
    
    try {
        const formData = new FormData();
        const csrfToken = getCSRFToken();
        
        if (csrfToken) {
            formData.append('csrfmiddlewaretoken', csrfToken);
        }
        
        const response = await fetch(`/cart/add/${productId}/`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: formData,
            credentials: 'same-origin'
        });
        
        if (!response.ok) throw new Error('Network error');
        
        const data = await response.json();
        
        if (data.success) {
            showToast(data.message || 'Товар добавлен в <a href="/cart/" style="color: #fff; text-decoration: underline; font-weight: bold;">корзину</a>!', 'success');
            updateCartCounter(data.cart_count);
            
            this.innerHTML = '✅ Добавлено!';
            setTimeout(() => {
                this.innerHTML = originalText;
                this.disabled = false;
                this.classList.remove('loading');
            }, 1500);
        } else {
            throw new Error(data.error || 'Ошибка при добавлении в корзину');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast(error.message || 'Ошибка при добавлении в корзину', 'error');
        
        this.innerHTML = originalText;
        this.disabled = false;
        this.classList.remove('loading');
    }
}

async function handleWishlistToggle(e) {
    e.preventDefault();
    const productId = this.getAttribute('data-product-id');
    const isInWishlist = this.classList.contains('in-wishlist');
    const icon = this.querySelector('.wishlist-icon');
    
    try {
        const formData = new FormData();
        const csrfToken = getCSRFToken();
        
        if (csrfToken) {
            formData.append('csrfmiddlewaretoken', csrfToken);
        }
        
        const response = await fetch(`/wishlist/toggle/${productId}/`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: formData,
            credentials: 'same-origin'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(data.message, 'success');
            
            updateWishlistCounter(data.wishlist_count);
            
            if (data.action === 'added') {
                this.classList.add('in-wishlist');
                if (icon) icon.textContent = '❤️';
                this.setAttribute('title', 'Удалить из избранного');
            } else {
                this.classList.remove('in-wishlist');
                if (icon) icon.textContent = '🤍';
                this.setAttribute('title', 'Добавить в избранное');
            }
            
            if (icon) {
                icon.style.transform = 'scale(1.3)';
                setTimeout(() => {
                    icon.style.transform = 'scale(1)';
                }, 300);
            }
            
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        showToast(error.message || 'Ошибка при работе с избранным', 'error');
    }
}

function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${type === 'success' ? '✅' : '❌'}</span>
        <span class="toast-message">${message}</span>
    `;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 100);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

function updateWishlistCounter(count) {
    console.log('Wishlist count updated:', count);
}

function updateCartCounter(count) {
    console.log('Cart count updated:', count);
}

function getCSRFToken() {
    let csrfToken = null;
    
    // 1. В hidden input
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfInput) {
        csrfToken = csrfInput.value;
    }
    
    // 2. В meta теге
    if (!csrfToken) {
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            csrfToken = metaToken.getAttribute('content');
        }
    }
    
    // 3. В куках
    if (!csrfToken) {
        const name = 'csrftoken';
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    csrfToken = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
    }
    
    return csrfToken;
}

document.addEventListener('DOMContentLoaded', function() {
    initializeProductHandlers();
    
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debouncedSearch);
    }
    
    const filterSelects = document.querySelectorAll('.filter-select');
    filterSelects.forEach(select => {
        select.addEventListener('change', updateFilters);
    });
    
    const priceInputs = document.querySelectorAll('.price-input');
    priceInputs.forEach(input => {
        input.addEventListener('change', updateFilters);
    });
    
    const inStockCheckbox = document.getElementById('inStockCheckbox');
    if (inStockCheckbox) {
        inStockCheckbox.addEventListener('change', updateFilters);
    }
    
    const clearFiltersBtn = document.getElementById('clearFiltersBtn');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', clearAllFilters);
    }
    
    let observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !isLoading) {
                const loadMoreBtn = document.querySelector('.pagination-btn');
                if (loadMoreBtn) {
                    loadMoreBtn.click();
                }
            }
        });
    });
    
    const sentinel = document.createElement('div');
    sentinel.id = 'scroll-sentinel';
    const productsContent = document.querySelector('.products-content');
    if (productsContent) {
        productsContent.appendChild(sentinel);
        observer.observe(sentinel);
    }
});

async function updatePriceRange() {
    const category = document.querySelector('select[name="category"]')?.value || '';
    const brand = document.querySelector('select[name="brand"]')?.value || '';
    
    try {
        const response = await fetch(`/api/price-range/?category=${encodeURIComponent(category)}&brand=${encodeURIComponent(brand)}`);
        const data = await response.json();
        
        const priceRangeInfo = document.querySelector('.price-range-info');
        if (priceRangeInfo) {
            priceRangeInfo.textContent = `Диапазон: ${data.min_price} - ${data.max_price} ₽`;
        }
    } catch (error) {
        console.error('Error updating price range:', error);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const categorySelect = document.querySelector('select[name="category"]');
    const brandSelect = document.querySelector('select[name="brand"]');
    
    if (categorySelect) {
        categorySelect.addEventListener('change', updatePriceRange);
    }
    if (brandSelect) {
        brandSelect.addEventListener('change', updatePriceRange);
    }
});