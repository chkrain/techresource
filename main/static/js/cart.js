document.addEventListener('DOMContentLoaded', function() {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    let updateTimeout;
    
    function showMessage(message, type = 'success') {
        const existingMessage = document.querySelector('.cart-message');
        if (existingMessage) {
            existingMessage.remove();
        }
        
        const messageEl = document.createElement('div');
        messageEl.className = `cart-message ${type}`;
        messageEl.textContent = message;
        document.body.appendChild(messageEl);
        
        setTimeout(() => messageEl.classList.add('show'), 100);
        
        setTimeout(() => {
            messageEl.classList.remove('show');
            setTimeout(() => messageEl.remove(), 300);
        }, 3000);
    }
    
    async function updateQuantity(itemId, newQuantity) {
        const itemElement = document.querySelector(`.cart-item[data-item-id="${itemId}"]`);
        if (!itemElement) return;
        itemElement.classList.add('quantity-updating');
        
        try {
            const response = await fetch(`/cart/update/${itemId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: `action=set&quantity=${newQuantity}`
            });
            
            const data = await response.json();
            
            if (data.success) {
                updateCartUI(itemId, newQuantity, data);
                itemElement.classList.add('quantity-updated');
                setTimeout(() => itemElement.classList.remove('quantity-updated'), 600);
                showMessage('Количество обновлено', 'success');
            } else {
                showMessage(data.error || 'Ошибка обновления', 'error');
                const input = itemElement.querySelector('.quantity-input');
                input.value = input.getAttribute('data-previous-value') || newQuantity;
            }
            
        } catch (error) {
            console.error('Error updating quantity:', error);
            showMessage('Ошибка соединения', 'error');
            const input = itemElement.querySelector('.quantity-input');
            input.value = input.getAttribute('data-previous-value') || newQuantity;
        } finally {
            itemElement.classList.remove('quantity-updating');
        }
    }

    async function removeItem(itemId) {
        if (!confirm('Вы уверены, что хотите удалить товар из корзины?')) {
            return;
        }
        
        const itemElement = document.querySelector(`.cart-item[data-item-id="${itemId}"]`);
        
        if (!itemElement) return;
        
        itemElement.classList.add('quantity-updating');
        
        try {
            const response = await fetch(`/cart/update/${itemId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: 'action=remove'
            });
            
            const data = await response.json();
            
            if (data.success) {
                itemElement.style.opacity = '0';
                itemElement.style.transform = 'translateX(-100px)';
                setTimeout(() => {
                    itemElement.remove();
                    updateCartSummary(data);
                    
                    if (data.item_count === 0) {
                        location.reload();
                    }
                }, 300);
                
                showMessage('Товар удален из корзины', 'success');
            } else {
                showMessage(data.error || 'Ошибка удаления', 'error');
                itemElement.classList.remove('quantity-updating');
            }
            
        } catch (error) {
            console.error('Error removing item:', error);
            showMessage('Ошибка соединения', 'error');
            itemElement.classList.remove('quantity-updating');
        }
    }
    
    function updateCartUI(itemId, newQuantity, data) {
        const itemElement = document.querySelector(`.cart-item[data-item-id="${itemId}"]`);
        const price = parseFloat(itemElement.querySelector('.quantity-input').getAttribute('data-price'));
        const totalPrice = price * newQuantity;
        const input = itemElement.querySelector('.quantity-input');
        input.value = newQuantity;
        input.setAttribute('data-previous-value', newQuantity);
        itemElement.querySelector('.total-price').textContent = `${totalPrice.toFixed(2)} ₽`;
        itemElement.querySelector('.mobile-total-price').textContent = totalPrice.toFixed(2);
        const decreaseBtn = itemElement.querySelector('.decrease');
        const increaseBtn = itemElement.querySelector('.increase');
        const maxQuantity = parseInt(itemElement.querySelector('.quantity-input').getAttribute('data-max-quantity'));
        decreaseBtn.disabled = newQuantity <= 1;
        increaseBtn.disabled = newQuantity >= maxQuantity;
        updateCartSummary(data);
    }

    function updateCartSummary(data) {
        const formattedTotal = parseFloat(data.cart_total).toLocaleString('ru-RU', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        
        document.getElementById('subtotal-price').textContent = `${formattedTotal} ₽`;
        
        document.getElementById('final-price').textContent = `${formattedTotal} ₽`;
        
        const itemsCountElement = document.querySelector('.items-count');
        if (itemsCountElement) {
            itemsCountElement.textContent = `${data.item_count} товар(ов)`;
        }
        
        if (data.vat_total !== undefined) {
            const vatTotal = Math.round(parseFloat(data.vat_total));
            document.getElementById('vat-total').textContent = `${vatTotal} ₽`;
        }
        
        if (data.vat_rate !== undefined) {
            const vatRateElement = document.getElementById('vat-rate');
            if (vatRateElement) {
                vatRateElement.textContent = Math.round(parseFloat(data.vat_rate));
            }
        }
    }
    
    document.querySelectorAll('.quantity-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const itemId = this.getAttribute('data-item-id');
            const input = document.querySelector(`.quantity-input[data-item-id="${itemId}"]`);
            let currentValue = parseInt(input.value);
            const maxQuantity = parseInt(input.getAttribute('data-max-quantity'));
            
            if (this.classList.contains('increase') && currentValue < maxQuantity) {
                const newValue = currentValue + 1;
                input.value = newValue;
                updateQuantity(itemId, newValue);
            } else if (this.classList.contains('decrease') && currentValue > 1) {
                const newValue = currentValue - 1;
                input.value = newValue;
                updateQuantity(itemId, newValue);
            }
        });
    });

    document.querySelectorAll('.quantity-input').forEach(input => {
        input.setAttribute('data-previous-value', input.value);
        
        input.addEventListener('change', function() {
            const itemId = this.getAttribute('data-item-id');
            let newValue = parseInt(this.value);
            const maxQuantity = parseInt(this.getAttribute('data-max-quantity'));
            
            if (isNaN(newValue) || newValue < 1) {
                newValue = 1;
            } else if (newValue > maxQuantity) {
                newValue = maxQuantity;
                showMessage(`Максимальное количество: ${maxQuantity}`, 'info');
            }
            
            this.value = newValue;
            this.setAttribute('data-previous-value', newValue);
            
            updateQuantity(itemId, newValue);
        });
        
        input.addEventListener('input', function() {
            clearTimeout(updateTimeout);
            const itemId = this.getAttribute('data-item-id');
            const value = this.value;
            
            if (/^\d+$/.test(value) && parseInt(value) > 0) {
                updateTimeout = setTimeout(() => {
                    this.setAttribute('data-previous-value', value);
                    updateQuantity(itemId, value);
                }, 1000);
            }
        });
        
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.blur(); // Убираем фокус, чтобы сработал change
            }
        });
    });
    
    document.querySelectorAll('.update-quantity-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const itemId = this.getAttribute('data-item-id');
            const input = document.querySelector(`.quantity-input[data-item-id="${itemId}"]`);
            const newValue = parseInt(input.value);
            
            if (!isNaN(newValue) && newValue > 0) {
                updateQuantity(itemId, newValue);
            } else {
                showMessage('Введите корректное количество', 'error');
            }
        });
    });
    
    document.querySelectorAll('.remove-item-btn, .remove-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const itemId = this.getAttribute('data-item-id');
            removeItem(itemId);
        });
    });
});

document.addEventListener('DOMContentLoaded', function() {
    function initCustomSelect() {
        const originalSelect = document.getElementById('address-select');
        const customSelect = document.querySelector('.custom-select');
        const customTrigger = document.querySelector('.custom-select-trigger');
        const customOptions = document.querySelector('.custom-select-options');
        const customSelectWrapper = document.querySelector('.custom-select-wrapper');
        
        if (!originalSelect || !customSelect) return;
        
        function updateCustomSelectDisplay() {
            const selectedOption = originalSelect.options[originalSelect.selectedIndex];
            
            if (selectedOption.value) {
                const textParts = selectedOption.text.split('|');
                customTrigger.innerHTML = `
                    <span class="selected-text">
                        <span class="option-title">${textParts[0] || 'Адрес'}</span>
                        <span class="option-details">${textParts[1] || 'Не указан'}</span>
                    </span>
                    <span class="custom-arrow">▼</span>
                `;
                customTrigger.classList.remove('placeholder');
                customSelectWrapper.classList.remove('error');
                customSelectWrapper.classList.add('success');
                
                if (customOptions) {
                    customOptions.querySelectorAll('.custom-select-option').forEach(opt => {
                        opt.classList.remove('selected');
                        if (opt.getAttribute('data-value') === selectedOption.value) {
                            opt.classList.add('selected');
                        }
                    });
                }
            } else {
                customTrigger.innerHTML = `
                    <span class="selected-text">Выберите адрес доставки</span>
                    <span class="custom-arrow">▼</span>
                `;
                customTrigger.classList.add('placeholder');
                customSelectWrapper.classList.remove('success');
            }
        }
        
        updateCustomSelectDisplay();
        
        if (customTrigger) {
            customTrigger.addEventListener('click', function(e) {
                e.stopPropagation();
                const isOpen = customSelect.classList.contains('open');
                
                document.querySelectorAll('.custom-select.open').forEach(select => {
                    if (select !== customSelect) {
                        select.classList.remove('open');
                    }
                });
                
                customSelect.classList.toggle('open');
                
                if (!isOpen && customOptions) {
                    const selectedOption = customOptions.querySelector('.custom-select-option.selected');
                    if (selectedOption) {
                        selectedOption.scrollIntoView({ block: 'nearest' });
                    }
                }
            });
        }
        
        if (customOptions) {
            customOptions.querySelectorAll('.custom-select-option').forEach(option => {
                option.addEventListener('click', function() {
                    const value = this.getAttribute('data-value');
                    
                    originalSelect.value = value;
                    
                    updateCustomSelectDisplay();
                    
                    customSelect.classList.remove('open');
                });
            });
        }
        
        // Закрытие при клике вне элемента
        document.addEventListener('click', function(e) {
            if (customSelect && !customSelect.contains(e.target)) {
                customSelect.classList.remove('open');
            }
        });
        
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && customSelect && customSelect.classList.contains('open')) {
                customSelect.classList.remove('open');
            }
        });
        
        originalSelect.addEventListener('change', function() {
            updateCustomSelectDisplay();
        });
    }
    
    if (document.getElementById('address-select')) {
        initCustomSelect();
    }
    
    const orderForm = document.querySelector('.order-form');
    if (orderForm) {
        orderForm.addEventListener('submit', function(e) {
            const addressSelect = document.getElementById('address-select');
            const customSelectWrapper = document.querySelector('.custom-select-wrapper');
            
            if (addressSelect && (!addressSelect.value || addressSelect.value === '')) {
                if (customSelectWrapper) {
                    customSelectWrapper.classList.add('error');
                    customSelectWrapper.classList.remove('success');
                    
                    let errorMessage = customSelectWrapper.querySelector('.custom-error-message');
                    if (!errorMessage) {
                        errorMessage = document.createElement('div');
                        errorMessage.className = 'custom-error-message';
                        errorMessage.style.cssText = `
                            color: #e53e3e;
                            font-size: 0.8rem;
                            margin-top: 0.25rem;
                            padding: 0.25rem 0.5rem;
                            background: #fed7d7;
                            border-radius: 4px;
                            border-left: 3px solid #e53e3e;
                        `;
                        customSelectWrapper.appendChild(errorMessage);
                    }
                    errorMessage.textContent = 'Пожалуйста, выберите адрес доставки';
                }
                
                e.preventDefault();
                
                if (customSelectWrapper) {
                    customSelectWrapper.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    
                    const customSelect = document.querySelector('.custom-select');
                    if (customSelect) {
                        customSelect.classList.add('open');
                    }
                }
            } else {
                if (customSelectWrapper) {
                    customSelectWrapper.classList.remove('error');
                    const errorMessage = customSelectWrapper.querySelector('.custom-error-message');
                    if (errorMessage) {
                        errorMessage.remove();
                    }
                }
            }
        });
    }
});