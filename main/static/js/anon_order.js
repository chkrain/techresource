document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const fileUploadArea = document.querySelector('.file-upload-area');
    const filePreview = document.getElementById('filePreview');
    const maxSize = 10 * 1024 * 1024; 
    
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Б';
        const k = 1024;
        const sizes = ['Б', 'КБ', 'МБ', 'ГБ'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    function getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const icons = {
            'pdf': '📄',
            'doc': '📝',
            'docx': '📝',
            'xls': '📊',
            'xlsx': '📊',
            'jpg': '🖼️',
            'jpeg': '🖼️',
            'png': '🖼️',
            'zip': '🗜️',
            'rar': '🗜️'
        };
        return icons[ext] || '📎';
    }
    
    function updatePreview() {
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            
            // Проверка размера
            if (file.size > maxSize) {
                alert('Файл слишком большой. Максимальный размер: 10 МБ');
                fileInput.value = '';
                return;
            }
            
            // Создаем превью
            filePreview.innerHTML = `
                <div class="file-item">
                    <div class="file-info">
                        <div class="file-icon">${getFileIcon(file.name)}</div>
                        <div class="file-details">
                            <div class="file-name">${file.name}</div>
                            <div class="file-size">${formatFileSize(file.size)}</div>
                        </div>
                    </div>
                    <button type="button" class="file-remove" onclick="removeFile()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            
            filePreview.classList.add('show');
            fileUploadArea.classList.remove('drag-over');
        }
    }
    
    fileInput.addEventListener('change', updatePreview);
    
    window.removeFile = function() {
        fileInput.value = '';
        filePreview.classList.remove('show');
        filePreview.innerHTML = '';
    };
    
    ['dragenter', 'dragover'].forEach(eventName => {
        fileUploadArea.addEventListener(eventName, function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.add('drag-over');
        });
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        fileUploadArea.addEventListener(eventName, function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.remove('drag-over');
        });
    });
    
    fileUploadArea.addEventListener('drop', function(e) {
        const dt = e.dataTransfer;
        fileInput.files = dt.files;
        updatePreview();
    });
});

async function loadAnonymousCartItems() {
    console.log("🔄 Загружаем товары из анонимной корзины...");
    
    try {
        const response = await fetch('/anonymous-cart/items/', {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        console.log("📨 Ответ от сервера получен");
        const data = await response.json();
        console.log("📊 Данные корзины:", data);
        
        if (data.success) {
            renderCartItems(data.items, data.total);
        } else {
            console.log("ℹ️ Корзина пуста или ошибка");
            const cartItemsContainer = document.getElementById('anonymousCartItems');
            if (cartItemsContainer) {
                cartItemsContainer.innerHTML = `
                    <div class="empty-cart">
                        <div class="empty-cart-icon">🛒</div>
                        <h3>Корзина пуста</h3>
                        <p>Добавьте товары из каталога, чтобы сделать заказ</p>
                        <a href="{% url 'products' %}" class="btn btn-primary" style="display: inline-block; margin-top: 1rem;">
                            📦 Перейти к покупкам
                        </a>
                    </div>
                `;
            }
            
            const itemsCountElement = document.getElementById('itemsCount');
            if (itemsCountElement) {
                itemsCountElement.textContent = '0 товар(ов)';
            }
        }
    } catch (error) {
        console.error('❌ Ошибка загрузки корзины:', error);
        const cartItemsContainer = document.getElementById('anonymousCartItems');
        if (cartItemsContainer) {
            cartItemsContainer.innerHTML = `
                <div class="empty-cart">
                    <div class="empty-cart-icon">⚠️</div>
                    <h3>Ошибка загрузки</h3>
                    <p>Попробуйте обновить страницу</p>
                </div>
            `;
        }
    }
}

function renderCartItems(items, total) {
    console.log("🛒 Рендерим товары:", items);
    
    if (items.length === 0) {
        document.getElementById('anonymousCartItems').innerHTML = `
            <div class="empty-cart">
                <div class="empty-cart-icon">🛒</div>
                <h3>Корзина пуста</h3>
                <p>Добавьте товары из каталога, чтобы сделать заказ</p>
                <a href="{% url 'products' %}" class="btn btn-primary" style="display: inline-block; margin-top: 1rem;">
                    📦 Перейти к покупкам
                </a>
            </div>
        `;
        
        // Проверяем существует ли элемент перед обновлением
        const itemsCountElement = document.getElementById('itemsCount');
        if (itemsCountElement) {
            itemsCountElement.textContent = '0 товар(ов)';
        }
        return;
    }
    
    // Проверяем существует ли элемент перед обновлением
    const itemsCountElement = document.getElementById('itemsCount');
    if (itemsCountElement) {
        itemsCountElement.textContent = `${items.length} товар(ов)`;
    }
    
    let html = '';
    
    items.forEach(item => {
        const itemTotal = parseFloat(item.total);
        const price = parseFloat(item.price);
        const maxQuantity = item.max_quantity || 999;
        
        html += `
            <div class="cart-item" data-product-id="${item.product_id}">
                <div class="item-image">
                    ${item.image ? `<img src="${item.image}" alt="${item.name}" loading="lazy">` : `
                        <div class="image-placeholder">
                            <span class="placeholder-icon">⚙️</span>
                        </div>
                    `}
                </div>
                
                <div class="item-details">
                    <h3 class="item-title">${item.name}</h3>
                    ${item.article ? `<p class="item-article">Артикул: ${item.article}</p>` : ''}
                    
                    <div class="item-price-mobile">
                        <span class="price">${price.toFixed(2)} ₽</span>
                        <span class="total">Итого: <span class="mobile-total-price">${itemTotal.toFixed(2)}</span> ₽</span>
                    </div>
                </div>
                
                <div class="item-quantity">
                    <div class="quantity-controls">
                        <button class="quantity-btn decrease" type="button" onclick="updateQuantity(${item.product_id}, -1)" ${item.quantity <= 1 ? 'disabled' : ''}>
                            −
                        </button>
                        
                        <input type="number" class="quantity-input" value="${item.quantity}" 
                               min="1" max="${maxQuantity}" 
                               onchange="updateQuantity(${item.product_id}, 0, this.value)"
                               data-price="${price}"
                               data-max-quantity="${maxQuantity}">
                        
                        <button class="quantity-btn increase" type="button" onclick="updateQuantity(${item.product_id}, 1)" ${item.quantity >= maxQuantity ? 'disabled' : ''}>
                            +
                        </button>
                    </div>
                </div>
                
                <div class="item-price">
                    <div class="price-per-item">${price.toFixed(2)} ₽/шт</div>
                    <div class="total-price">${itemTotal.toFixed(2)} ₽</div>
                </div>
                
                <div class="item-remove">
                    <button class="remove-btn" type="button" onclick="removeFromCart(${item.product_id})" title="Удалить из заказа">
                        🗑️
                    </button>
                </div>
            </div>
        `;
    });
    
    html += `
        <div class="summary-total">
            <span>Итого к оплате:</span>
            <span class="total-amount">${parseFloat(total).toFixed(2)} ₽</span>
        </div>
    `;
    
    document.getElementById('anonymousCartItems').innerHTML = html;
}

async function updateQuantity(productId, delta, newValue = null) {
    try {
        const response = await fetch('/anonymous-cart/update/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                product_id: productId,
                delta: delta,
                quantity: newValue
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            loadAnonymousCartItems();
            updateCartCounter(data.cart_count);
            showToast('Количество обновлено', 'success');
        } else {
            showToast(data.error || 'Ошибка обновления', 'error');
        }
    } catch (error) {
        console.error('Error updating quantity:', error);
        showToast('Ошибка соединения', 'error');
    }
}

async function removeFromCart(productId) {
    if (!confirm('Вы уверены, что хотите удалить товар из заказа?')) {
        return;
    }
    
    try {
        const response = await fetch('/anonymous-cart/remove/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ product_id: productId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            loadAnonymousCartItems();
            updateCartCounter(data.cart_count);
            showToast('Товар удален из заказа', 'success');
        }
    } catch (error) {
        console.error('Error removing item:', error);
        showToast('Ошибка соединения', 'error');
    }
}

function updateCartCounter(count) {
    const cartCount = document.getElementById('anonymousCartCount');
    if (cartCount) {
        cartCount.textContent = count;
        cartCount.style.display = count > 0 ? 'inline-block' : 'none';
    }
}

function showToast(message, type = 'success') {
    const messageEl = document.createElement('div');
    messageEl.className = `cart-message ${type}`;
    messageEl.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        color: white;
        font-weight: 600;
        z-index: 10000;
        transform: translateX(400px);
        transition: transform 0.3s ease;
        max-width: 300px;
    `;
    
    if (type === 'success') {
        messageEl.style.background = '#48bb78';
    } else if (type === 'error') {
        messageEl.style.background = '#e53e3e';
    } else {
        messageEl.style.background = '#0052cc';
    }
    
    messageEl.textContent = message;
    document.body.appendChild(messageEl);
    
    setTimeout(() => messageEl.style.transform = 'translateX(0)', 100);
    
    setTimeout(() => {
        messageEl.style.transform = 'translateX(400px)';
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.remove();
            }
        }, 300);
    }, 3000);
}

document.getElementById('anonymousOrderForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const submitBtn = this.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    const requiredFields = this.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.style.borderColor = '#e53e3e';
            isValid = false;
        } else {
            field.style.borderColor = '#e9ecef';
        }
    });
    
    if (!isValid) {
        showToast('Заполните все обязательные поля', 'error');
        return;
    }
    
    submitBtn.innerHTML = '⏳ Отправляем...';
    submitBtn.disabled = true;
    
    try {
        const response = await fetch('/anonymous-cart/create-order/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('✅ Заявка отправлена! Счет будет выставлен в течение рабочего дня.', 'success');
            setTimeout(() => {
                window.location.href = '/';
            }, 2000);
        } else {
            showToast(data.error || 'Ошибка отправки заявки', 'error');
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }
    } catch (error) {
        console.error('Error submitting order:', error);
        showToast('Ошибка соединения', 'error');
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
});

function getCSRFToken() {
    let csrfToken = null;
    
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfInput) {
        csrfToken = csrfInput.value;
    }
    
    if (!csrfToken) {
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            csrfToken = metaToken.getAttribute('content');
        }
    }
    
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
    loadAnonymousCartItems();
});