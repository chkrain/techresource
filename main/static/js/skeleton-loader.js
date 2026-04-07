// Skeleton Loader
class SkeletonLoader {
    constructor() {
        this.skeletonContainer = null;
        this.originalContent = null;
    }

    // Показать скелетон
    showSkeleton(containerId, skeletonType = 'default') {
        const container = document.getElementById(containerId);
        if (!container) return;

        // Сохраняем оригинальное содержимое
        this.originalContent = container.innerHTML;
        
        // Очищаем контейнер
        container.innerHTML = '';
        
        // Создаем контейнер для скелетона
        this.skeletonContainer = document.createElement('div');
        this.skeletonContainer.className = 'page-skeleton';
        
        // Генерируем скелетон в зависимости от типа
        switch(skeletonType) {
            case 'products':
                this.skeletonContainer.innerHTML = this.getProductsSkeleton();
                break;
            case 'product-detail':
                this.skeletonContainer.innerHTML = this.getProductDetailSkeleton();
                break;
            case 'services':
                this.skeletonContainer.innerHTML = this.getServicesSkeleton();
                break;
            case 'cart':
                this.skeletonContainer.innerHTML = this.getCartSkeleton();
                break;
            case 'reviews':
                this.skeletonContainer.innerHTML = this.getReviewsSkeleton();
                break;
            default:
                this.skeletonContainer.innerHTML = this.getDefaultSkeleton();
        }
        
        container.appendChild(this.skeletonContainer);
    }

    // Скрыть скелетон и показать контент
    hideSkeleton(containerId, content) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        container.innerHTML = content || this.originalContent;
        this.skeletonContainer = null;
        this.originalContent = null;
    }

    // Скелетон для списка товаров
    getProductsSkeleton() {
        let html = '<div class="products-grid-skeleton">';
        for (let i = 0; i < 8; i++) {
            html += `
                <div class="product-card-skeleton">
                    <div class="product-image-skeleton skeleton"></div>
                    <div class="product-title-skeleton skeleton"></div>
                    <div class="product-price-skeleton skeleton"></div>
                    <div class="product-button-skeleton skeleton"></div>
                </div>
            `;
        }
        html += '</div>';
        return html;
    }

    // Скелетон для детальной страницы товара
    getProductDetailSkeleton() {
        return `
            <div class="product-detail-skeleton">
                <div class="product-gallery-skeleton skeleton"></div>
                <div class="product-info-skeleton">
                    <div class="skeleton-title skeleton"></div>
                    <div class="skeleton-text skeleton"></div>
                    <div class="skeleton-text skeleton"></div>
                    <div class="skeleton-text-short skeleton"></div>
                    <div class="skeleton-text skeleton"></div>
                    <div class="product-price-skeleton skeleton"></div>
                    <div class="product-button-skeleton skeleton"></div>
                </div>
            </div>
        `;
    }

    // Скелетон для списка услуг
    getServicesSkeleton() {
        let html = '';
        for (let i = 0; i < 4; i++) {
            html += `
                <div class="service-card-skeleton">
                    <div class="service-icon-skeleton skeleton"></div>
                    <div class="service-title-skeleton skeleton"></div>
                    <div class="service-description-skeleton skeleton"></div>
                </div>
            `;
        }
        return html;
    }

    // Скелетон для корзины
    getCartSkeleton() {
        let html = '';
        for (let i = 0; i < 3; i++) {
            html += `
                <div class="cart-item-skeleton">
                    <div class="cart-image-skeleton skeleton"></div>
                    <div class="cart-details-skeleton">
                        <div class="cart-title-skeleton skeleton"></div>
                        <div class="cart-price-skeleton skeleton"></div>
                    </div>
                </div>
            `;
        }
        return html;
    }

    // Скелетон для отзывов
    getReviewsSkeleton() {
        let html = '';
        for (let i = 0; i < 3; i++) {
            html += `
                <div class="review-skeleton">
                    <div class="review-avatar-skeleton skeleton"></div>
                    <div class="review-content-skeleton">
                        <div class="cart-title-skeleton skeleton"></div>
                        <div class="skeleton-text skeleton"></div>
                        <div class="skeleton-text skeleton"></div>
                    </div>
                </div>
            `;
        }
        return html;
    }

    // Скелетон по умолчанию
    getDefaultSkeleton() {
        return `
            <div style="padding: 20px;">
                <div class="skeleton-title skeleton" style="margin-bottom: 20px;"></div>
                <div class="skeleton-text skeleton" style="margin-bottom: 10px;"></div>
                <div class="skeleton-text skeleton" style="margin-bottom: 10px;"></div>
                <div class="skeleton-text skeleton" style="margin-bottom: 10px;"></div>
                <div class="skeleton-text-short skeleton"></div>
            </div>
        `;
    }
}

// Инициализация глобального объекта
window.skeletonLoader = new SkeletonLoader();

// Автоматическая загрузка скелетонов для страниц с AJAX
document.addEventListener('DOMContentLoaded', function() {
    // Перехватываем все ссылки и формы для добавления скелетонов
    const links = document.querySelectorAll('a:not([data-no-skeleton])');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            // Проверяем, что ссылка ведет на страницу в том же домене
            const href = this.getAttribute('href');
            if (href && !href.startsWith('http') && !href.startsWith('#') && !href.startsWith('javascript:')) {
                // Показываем скелетон перед переходом
                const mainContent = document.querySelector('.main-content .container');
                if (mainContent) {
                    const skeletonType = getSkeletonTypeFromUrl(href);
                    window.skeletonLoader.showSkeleton(mainContent.id || 'mainContent', skeletonType);
                }
            }
        });
    });
});

// Определяем тип скелетона по URL
function getSkeletonTypeFromUrl(url) {
    if (url.includes('/products/') && !url.match(/\/products\/\d+/)) {
        return 'products';
    } else if (url.includes('/products/') && url.match(/\/products\/\d+/)) {
        return 'product-detail';
    } else if (url.includes('/services/')) {
        return 'services';
    } else if (url.includes('/cart/')) {
        return 'cart';
    } else {
        return 'default';
    }
}