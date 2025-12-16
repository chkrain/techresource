document.addEventListener('DOMContentLoaded', function() {
    // Функция для показа toast уведомлений
    function showToast(message, type = 'success') {
        const toastContainer = document.getElementById('toast-container');
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
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // Функция для обновления счетчиков в хедере
    function updateHeaderCounters(wishlistCount, cartCount) {
        // Обновляем счетчик избранного в хедере
        const wishlistBadge = document.querySelector('.wishlist-count-badge');
        const wishlistLink = document.querySelector('a[href*="/wishlist/"]');
        
        if (wishlistCount > 0) {
            if (!wishlistBadge) {
                const newBadge = document.createElement('span');
                newBadge.className = 'cart-badge wishlist-count-badge';
                wishlistLink.appendChild(newBadge);
            }
            document.querySelector('.wishlist-count-badge').textContent = wishlistCount;
        } else if (wishlistBadge) {
            wishlistBadge.remove();
        }
        
        // Обновляем счетчик корзины
        if (cartCount !== undefined) {
            const cartBadge = document.querySelector('.avatar-badge');
            if (cartCount > 0) {
                if (!cartBadge) {
                    const userAvatar = document.querySelector('.user-avatar');
                    const newBadge = document.createElement('span');
                    newBadge.className = 'avatar-badge';
                    userAvatar.appendChild(newBadge);
                }
                document.querySelector('.avatar-badge').textContent = cartCount;
            } else if (cartBadge) {
                cartBadge.remove();
            }
        }
    }

    // Функция для получения CSRF токена
    function getCSRFToken() {
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfInput) {
            return csrfInput.value;
        }
        
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            return metaToken.getAttribute('content');
        }
        
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Удаление товара из избранного
    document.querySelectorAll('.remove-wishlist-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const productId = this.getAttribute('data-product-id');
            const wishlistItem = this.closest('.wishlist-item');
            
            try {
                const response = await fetch(`/wishlist/remove/${productId}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCSRFToken(),
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    credentials: 'same-origin'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showToast(data.message, 'success');
                    updateHeaderCounters(data.wishlist_count);
                    
                    // Анимация удаления
                    wishlistItem.style.opacity = '0';
                    wishlistItem.style.transform = 'translateX(-100px)';
                    setTimeout(() => {
                        wishlistItem.remove();
                        
                        const remainingItems = document.querySelectorAll('.wishlist-item');
                        if (remainingItems.length === 0) {
                            location.reload(); // Перезагружаем для показа пустого состояния
                        }
                    }, 300);
                } else {
                    throw new Error(data.error);
                }
            } catch (error) {
                console.error('Error:', error);
                showToast(error.message || 'Ошибка при удалении из избранного', 'error');
            }
        });
    });

    document.querySelectorAll('.move-to-cart-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const productId = this.getAttribute('data-product-id');
            const originalText = this.innerHTML;
            
            this.innerHTML = '⏳ Добавляем...';
            this.disabled = true;
            
            try {
                const response = await fetch(`/wishlist/to-cart/${productId}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCSRFToken(),
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    credentials: 'same-origin'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showToast(data.message, 'success');
                    updateHeaderCounters(data.wishlist_count, data.cart_count);
                    
                    this.innerHTML = '✅ Добавлено!';
                    
                    const wishlistItem = this.closest('.wishlist-item');
                    setTimeout(() => {
                        wishlistItem.style.opacity = '0';
                        wishlistItem.style.transform = 'translateX(-100px)';
                        setTimeout(() => {
                            wishlistItem.remove();
                            
                            const remainingItems = document.querySelectorAll('.wishlist-item');
                            if (remainingItems.length === 0) {
                                location.reload();
                            }
                        }, 300);
                    }, 1000);
                } else {
                    throw new Error(data.error);
                }
            } catch (error) {
                console.error('Error:', error);
                showToast(error.message || 'Ошибка при добавлении в корзину', 'error');
                
                this.innerHTML = originalText;
                this.disabled = false;
            }
        });
    });

    const clearWishlistBtn = document.getElementById('clearWishlistBtn');
    if (clearWishlistBtn) {
        clearWishlistBtn.addEventListener('click', async function() {
            if (!confirm('Вы уверены, что хотите очистить всё избранное? Это действие нельзя отменить.')) {
                return;
            }
            
            const originalText = this.innerHTML;
            this.innerHTML = '⏳ Очищаем...';
            this.disabled = true;
            
            try {
                const response = await fetch('/wishlist/clear/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCSRFToken(),
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    credentials: 'same-origin'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showToast(data.message, 'success');
                    updateHeaderCounters(data.wishlist_count);
                    
                    const items = document.querySelectorAll('.wishlist-item');
                    items.forEach((item, index) => {
                        setTimeout(() => {
                            item.style.opacity = '0';
                            item.style.transform = 'translateX(-100px)';
                        }, index * 100);
                    });
                    
                    setTimeout(() => {
                        location.reload();
                    }, items.length * 100 + 300);
                } else {
                    throw new Error(data.error);
                }
            } catch (error) {
                console.error('Error:', error);
                showToast(error.message || 'Ошибка при очистке избранного', 'error');
                
                this.innerHTML = originalText;
                this.disabled = false;
            }
        });
    }
});