document.addEventListener('DOMContentLoaded', function() {
    AOS.init({
        duration: 800,
        once: true,
        offset: 100
    });

    anime({
        targets: '.hero-title',
        translateY: [30, 0],
        opacity: [0, 1],
        duration: 1000,
        easing: 'easeOutCubic'
    });

    anime({
        targets: '.hero-subtitle',
        translateY: [30, 0],
        opacity: [0, 1],
        duration: 1000,
        delay: 300,
        easing: 'easeOutCubic'
    });

    document.querySelectorAll('.timeline-toggle').forEach(btn => {
        btn.addEventListener('click', function() {
            const orderId = this.getAttribute('data-order-id');
            const timeline = document.getElementById(`timeline-${orderId}`);
            const isVisible = timeline.style.display === 'block';
            
            if (isVisible) {
                anime({
                    targets: timeline,
                    opacity: [1, 0],
                    height: [timeline.scrollHeight + 'px', 0],
                    duration: 400,
                    easing: 'easeOutCubic',
                    complete: function() {
                        timeline.style.display = 'none';
                    }
                });
                this.classList.remove('active');
            } else {
                timeline.style.display = 'block';
                anime({
                    targets: timeline,
                    opacity: [0, 1],
                    height: [0, timeline.scrollHeight + 'px'],
                    duration: 500,
                    easing: 'easeOutCubic'
                });
                this.classList.add('active');
                
                animateTimelineLine(timeline);
            }
        });
    });

    function animateTimelineLine(timeline) {
        const timelineContainer = timeline.querySelector('.timeline-container');
        const steps = timeline.querySelectorAll('.timeline-step');
        let completedSteps = 0;
        
        steps.forEach(step => {
            if (step.classList.contains('completed') || step.classList.contains('current')) {
                completedSteps++;
            }
        });
        
        if (completedSteps > 0) {
            const totalSteps = steps.length;
            const fillHeight = (completedSteps / totalSteps) * 100;
            
            const filledLine = timelineContainer.querySelector('.timeline-filled-line') || 
                              document.createElement('div');
            filledLine.className = 'timeline-filled-line';
            filledLine.style.cssText = `
                position: absolute;
                left: 25px;
                top: 0;
                width: 3px;
                background: linear-gradient(to bottom, #27ae60, #2ecc71);
                border-radius: 2px;
                height: 0;
                z-index: 1;
                transition: height 1.5s ease;
            `;
            
            if (!timelineContainer.querySelector('.timeline-filled-line')) {
                timelineContainer.appendChild(filledLine);
            }
            
            anime({
                targets: filledLine,
                height: `${fillHeight}%`,
                duration: 1500,
                easing: 'easeOutCubic',
                delay: 300
            });
        }
    }

    function getCSRFToken() {
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

    document.querySelectorAll('.reorder-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const orderId = this.getAttribute('data-order-id');
            const orderCard = this.closest('.order-card');
            
            anime({
                targets: this,
                scale: [1, 0.95, 1],
                duration: 200,
                easing: 'easeInOutQuad'
            });
            
            try {
                const originalText = this.innerHTML;
                this.innerHTML = '⏳ Добавляем в корзину...';
                this.disabled = true;
                
                const response = await fetch(`/order/${orderId}/reorder/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                const result = await response.json();
                
                if (result.success) {
                    await anime({
                        targets: this,
                        background: ['#28a745', '#155724'],
                        duration: 300,
                        easing: 'easeInOutQuad'
                    }).finished;
                    
                    this.innerHTML = '✅ Добавлено в корзину!';
                    
                    updateCartCounter(result.cart_count);
                    
                    showNotification(result.message, 'success');
                    
                    setTimeout(() => {
                        this.innerHTML = originalText;
                        this.disabled = false;
                        anime({
                            targets: this,
                            background: ['#155724', '#28a745'],
                            duration: 300
                        });
                    }, 2000);
                    
                } else {
                    throw new Error(result.error || 'Ошибка при повторении заказа');
                }
                
            } catch (error) {
                console.error('Ошибка при повторении заказа:', error);
                
                anime({
                    targets: this,
                    background: ['#28a745', '#dc3545'],
                    duration: 300
                });
                
                this.innerHTML = '❌ Ошибка';
                this.disabled = false;
                
                showNotification(error.message, 'error');
                
                setTimeout(() => {
                    this.innerHTML = '📋 Повторить заказ';
                    anime({
                        targets: this,
                        background: ['#dc3545', '#28a745'],
                        duration: 300
                    });
                }, 2000);
            }
        });
    });

    async function loadOrderDetails(orderId, orderCard, button) {
        try {
            const originalText = button.innerHTML;
            button.innerHTML = '⏳ Загрузка...';
            button.disabled = true;

            const response = await fetch(`/order/${orderId}/details/`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                const detailsSection = document.createElement('div');
                detailsSection.className = 'order-details-full';
                detailsSection.innerHTML = result.html;
                
                const orderContent = orderCard.querySelector('.order-content');
                orderContent.parentNode.insertBefore(detailsSection, orderContent.nextSibling);
                
                await anime({
                    targets: detailsSection,
                    opacity: [0, 1],
                    height: [0, detailsSection.scrollHeight + 'px'],
                    duration: 500,
                    easing: 'easeOutCubic'
                }).finished;
            
                button.innerHTML = '📄 Скрыть детали';
                button.disabled = false;
                
            } else {
                throw new Error(result.error || 'Ошибка загрузки деталей');
            }
            
        } catch (error) {
            console.error('Ошибка загрузки деталей заказа:', error);
            
            button.innerHTML = originalText;
            button.disabled = false;
            
            showNotification('Не удалось загрузить детали заказа', 'error');
        }
    }

    document.querySelectorAll('.details-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const orderId = this.getAttribute('data-order-id');
            const orderCard = this.closest('.order-card');
            
            anime({
                targets: this,
                scale: [1, 0.95, 1],
                duration: 200,
                easing: 'easeInOutQuad'
            });
            
            const detailsSection = orderCard.querySelector('.order-details-full');
            
            if (!detailsSection) {
                loadOrderDetails(orderId, orderCard, this);
            } else {
                toggleDetailsSection(detailsSection, this);
            }
        });
    });

    async function loadOrderDetails(orderId, orderCard) {
        try {
            const response = await fetch(`/order/${orderId}/details/`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                const detailsSection = document.createElement('div');
                detailsSection.className = 'order-details-full';
                detailsSection.innerHTML = result.html;
                
                const orderContent = orderCard.querySelector('.order-content');
                orderContent.parentNode.insertBefore(detailsSection, orderContent.nextSibling);
                
                anime({
                    targets: detailsSection,
                    opacity: [0, 1],
                    height: [0, detailsSection.scrollHeight + 'px'],
                    duration: 500,
                    easing: 'easeOutCubic'
                });
                
            } else {
                throw new Error(result.error || 'Ошибка загрузки деталей');
            }
            
        } catch (error) {
            console.error('Ошибка загрузки деталей заказа:', error);
            showNotification('Не удалось загрузить детали заказа', 'error');
        }
    }

    document.querySelectorAll('.cancel-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const orderId = this.getAttribute('data-order-id');
            const orderNumber = this.getAttribute('data-order-number');
            const orderCard = this.closest('.order-card');
            
            if (confirm('Вы уверены, что хотите отменить этот заказ?')) {
                const originalText = this.innerHTML;
                this.innerHTML = '⏳ Отмена...';
                this.disabled = true;

                try {
                    const response = await fetch(`/order/cancel/${orderId}/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCSRFToken(),
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });

                    const result = await response.json();

                    if (result.success) {
                        await anime({
                            targets: orderCard,
                            opacity: [1, 0],
                            translateY: [0, -20],
                            duration: 500,
                            easing: 'easeInOutQuad'
                        }).finished;

                        showNotification(result.message || 'Заказ успешно отменен', 'success');
                        
                        setTimeout(() => {
                            location.reload();
                        }, 1000);
                    } else {
                        throw new Error(result.error || 'Ошибка при отмене заказа');
                    }

                } catch (error) {
                    console.error('Ошибка при отмене заказа:', error);
                    
                    this.innerHTML = originalText;
                    this.disabled = false;
                    
                    showNotification(error.message || 'Произошла ошибка при отмене заказа', 'error');
                    
                    anime({
                        targets: orderCard,
                        translateX: [0, 10, -10, 0],
                        duration: 400,
                        easing: 'easeInOutQuad'
                    });
                }
            }
        });
    });

    function toggleDetailsSection(detailsSection, button) {
        const isVisible = detailsSection.style.display !== 'none';
        
        if (isVisible) {
            anime({
                targets: detailsSection,
                opacity: [1, 0],
                height: [detailsSection.scrollHeight + 'px', 0],
                duration: 400,
                easing: 'easeOutCubic',
                complete: function() {
                    detailsSection.style.display = 'none';
                    button.innerHTML = '📄 Детали';
                }
            });
        } else {
            detailsSection.style.display = 'block';
            anime({
                targets: detailsSection,
                opacity: [0, 1],
                height: [0, detailsSection.scrollHeight + 'px'],
                duration: 500,
                easing: 'easeOutCubic'
            });
            button.innerHTML = '📄 Скрыть детали';
        }
    }

    function updateCartCounter(newCount) {
        const cartCounter = document.querySelector('.cart-counter');
        if (cartCounter) {
            anime({
                targets: cartCounter,
                scale: [1, 1.5, 1],
                duration: 300,
                easing: 'easeInOutQuad'
            });
            cartCounter.textContent = newCount;
        }
    }

    document.querySelectorAll('.refund-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const orderId = this.getAttribute('data-order-id');
            window.location.href = `/order/${orderId}/request-refund/`;
        });
    });

    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-message">${message}</span>
                <button class="notification-close">&times;</button>
            </div>
        `;

        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#27ae60' : type === 'error' ? '#e74c3c' : '#3498db'};
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            max-width: 400px;
            animation: slideInRight 0.3s ease;
        `;

        notification.querySelector('.notification-content').style.cssText = `
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 15px;
        `;

        notification.querySelector('.notification-close').style.cssText = `
            background: none;
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
            padding: 0;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.animation = 'slideOutRight 0.3s ease';
                setTimeout(() => notification.remove(), 300);
            }
        }, 5000);

        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        });
    }

    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);

    document.querySelectorAll('.status-dot').forEach(dot => {
        anime({
            targets: dot,
            scale: [1, 1.2, 1],
            duration: 2000,
            loop: true,
            easing: 'easeInOutSine'
        });
    });

    document.querySelectorAll('.timeline-step').forEach((step, index) => {
        setTimeout(() => {
            anime({
                targets: step,
                translateX: [-20, 0],
                opacity: [0, 1],
                duration: 600,
                easing: 'easeOutCubic'
            });
        }, index * 200);
    });

    document.querySelectorAll('.step-icon').forEach(icon => {
        const step = icon.closest('.timeline-step');
        if (step.classList.contains('current')) {
            anime({
                targets: icon,
                scale: [1, 1.05, 1],
                duration: 2000,
                loop: true,
                easing: 'easeInOutSine'
            });
        }
    });

    document.querySelectorAll('.tracking-info').forEach(info => {
        anime({
            targets: info,
            opacity: [0, 1],
            translateY: [10, 0],
            duration: 800,
            delay: 600,
            easing: 'easeOutCubic'
        });
    });

    window.addEventListener('scroll', function() {
        const scrolled = window.pageYOffset;
        const hero = document.querySelector('.orders-hero');
        if (hero) {
            hero.style.transform = `translateY(${scrolled * 0.5}px)`;
        }
    });
});