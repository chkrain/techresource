document.addEventListener('DOMContentLoaded', function() {
    // Image Gallery
    const mainImage = document.getElementById('mainImage');
    const mainImageContainer = document.getElementById('mainImageContainer');
    const thumbnails = document.querySelectorAll('.thumbnail');
    const prevBtn = document.getElementById('prevImage');
    const nextBtn = document.getElementById('nextImage');
    const currentImageSpan = document.getElementById('currentImage');
    const totalImagesSpan = document.getElementById('totalImages');
    const imageCounter = document.getElementById('imageCounter');
    
    let currentImageIndex = 0;
    const totalImages = thumbnails.length;
    
    // Initialize gallery if there are multiple images
    if (totalImages > 1) {
        imageCounter.style.display = 'block';
        totalImagesSpan.textContent = totalImages;
        prevBtn.disabled = false;
        nextBtn.disabled = false;
        
        // Thumbnail click handlers
        thumbnails.forEach((thumbnail, index) => {
            thumbnail.addEventListener('click', function() {
                setActiveImage(index);
            });
        });
        
        // Navigation handlers
        prevBtn.addEventListener('click', function() {
            currentImageIndex = (currentImageIndex - 1 + totalImages) % totalImages;
            setActiveImage(currentImageIndex);
        });
        
        nextBtn.addEventListener('click', function() {
            currentImageIndex = (currentImageIndex + 1) % totalImages;
            setActiveImage(currentImageIndex);
        });
        
        // Keyboard navigation
        document.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowLeft') {
                prevBtn.click();
            } else if (e.key === 'ArrowRight') {
                nextBtn.click();
            }
        });
        
        // Swipe for mobile
        let touchStartX = 0;
        let touchEndX = 0;
        
        if (mainImageContainer) {
            mainImageContainer.addEventListener('touchstart', function(e) {
                touchStartX = e.changedTouches[0].screenX;
            });
            
            mainImageContainer.addEventListener('touchend', function(e) {
                touchEndX = e.changedTouches[0].screenX;
                handleSwipe();
            });
            
            function handleSwipe() {
                const swipeThreshold = 50;
                const diff = touchStartX - touchEndX;
                
                if (Math.abs(diff) > swipeThreshold) {
                    if (diff > 0) {
                        nextBtn.click();
                    } else {
                        prevBtn.click();
                    }
                }
            }
        }
    }
    
    function setActiveImage(index) {
        currentImageIndex = index;
        const thumbnail = thumbnails[index];
        const imageSrc = thumbnail.getAttribute('data-image-src');
        
        // Smooth image transition
        if (mainImage) {
            mainImage.style.opacity = '0';
            setTimeout(() => {
                mainImage.src = imageSrc;
                mainImage.style.opacity = '1';
            }, 200);
        }
        
        // Update active thumbnail
        thumbnails.forEach(thumb => {
            thumb.classList.remove('active');
            thumb.style.transform = 'scale(1)';
        });
        thumbnail.classList.add('active');
        thumbnail.style.transform = 'scale(1.05)';
        
        // Update counter
        currentImageSpan.textContent = index + 1;
    }
    
    // Add to Cart functionality
    const addToCartBtn = document.querySelector('.add-to-cart-btn');
    if (addToCartBtn) {
        addToCartBtn.addEventListener('click', handleAddToCart);
    }
    
    // Wishlist functionality
    const wishlistBtn = document.querySelector('.toggle-wishlist-btn');
    if (wishlistBtn) {
        wishlistBtn.addEventListener('click', handleWishlistToggle);
    }
    
    async function handleAddToCart(e) {
        e.preventDefault();
        const productId = this.getAttribute('data-product-id');
        const originalText = this.innerHTML;
        
        this.innerHTML = '<span class="btn-icon">⏳</span>Добавляем...';
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
                showToast(data.message || 'Товар добавлен в корзину!', 'success');
                
                this.innerHTML = '<span class="btn-icon">✅</span>Добавлено!';
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
        const isInWishlist = this.classList.contains('active');
        const icon = this.querySelector('.btn-icon');
        
        this.disabled = true;
        this.classList.add('loading');
        
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
                
                if (data.action === 'added') {
                    this.classList.add('active');
                    this.innerHTML = '<span class="btn-icon">❤️</span>В избранном';
                } else {
                    this.classList.remove('active');
                    this.innerHTML = '<span class="btn-icon">🤍</span>В избранное';
                }
                
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error:', error);
            showToast(error.message || 'Ошибка при работе с избранным', 'error');
        } finally {
            this.disabled = false;
            this.classList.remove('loading');
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
});