document.addEventListener('DOMContentLoaded', function() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    if (!csrfToken) {
        console.error('CSRF token not found!');
    }
    
    function updateCartCounter(quantity) {
        const cartCounters = [
            ...document.querySelectorAll('.cart-counter'),
            ...document.querySelectorAll('.cart-count'),
            ...document.querySelectorAll('[data-cart-count]'),
            ...document.querySelectorAll('.badge')
        ].filter(el => el.textContent.match(/\d+/)); 
        
        cartCounters.forEach(counter => {
            const oldValue = parseInt(counter.textContent) || 0;
            const newValue = quantity !== undefined ? quantity : oldValue + 1;
            
            counter.textContent = newValue;
            
            if (newValue > 0) {
                counter.style.display = 'inline-block';
            } else {
                counter.style.display = 'none';
            }
            
            if (window.anime) {
                anime({
                    targets: counter,
                    scale: [1, 1.3, 1],
                    duration: 300,
                    easing: 'easeInOutQuad'
                });
            }
        });
        
        if (cartCounters.length === 0) {
            console.log('Счетчики корзины не найдены. Количество:', quantity);
        }
    }
    
    function showCartNotification(message, type = 'success') {
        const existingNotification = document.querySelector('.cart-notification');
        if (existingNotification) {
            existingNotification.remove();
        }
        
        const notification = document.createElement('div');
        notification.className = `cart-notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-icon">${type === 'error' ? '❌' : '✅'}</span>
                <span class="notification-message">${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }, 3000);
    }
    
    document.querySelectorAll('.product-btn').forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const productId = this.getAttribute('data-product-id');
            const isAuthenticated = this.classList.contains('anonymous-quick-order') ? false : true;
            
            if (!productId) {
                console.error('Product ID not found');
                showCartNotification('Ошибка: ID товара не найден', 'error');
                return;
            }
            
            const originalText = this.textContent;
            const originalBackground = this.style.background;
            
            try {
                this.textContent = 'Добавляем...';
                this.classList.add('loading');
                this.disabled = true;
                
                const csrfToken = getCSRFToken();
                
                if (!csrfToken) {
                    console.error('CSRF token not found');
                    throw new Error('Ошибка безопасности. Попробуйте обновить страницу.');
                }
                
                let response, data;
                
                if (isAuthenticated) {
                    const formData = new FormData();
                    formData.append('csrfmiddlewaretoken', csrfToken);
                    formData.append('quantity', '1');
                    
                    response = await fetch('/cart/add/' + productId + '/', {
                        method: 'POST',
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        credentials: 'same-origin',
                        body: formData
                    });
                } else {
                    const formData = new FormData();
                    formData.append('quantity', '1');
                    formData.append('csrfmiddlewaretoken', csrfToken);
                    
                    response = await fetch(`/anonymous-cart/add/${productId}/`, {
                        method: 'POST',
                        body: formData,
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        credentials: 'same-origin'
                    });
                }
                
                if (!response.ok) {
                    if (response.status === 403) {
                        throw new Error('Ошибка безопасности. Попробуйте обновить страницу.');
                    }
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                data = await response.json();
                
                if (data.success) {
                    this.textContent = isAuthenticated ? '✓ В корзине' : '✓ В заказе';
                    this.style.background = '#28a745';
                    
                    updateCartCounter(data.cart_count || data.order_count || 0);
                    
                    if (window.anime) {
                        anime({
                            targets: this,
                            scale: [1, 1.1, 1],
                            duration: 300,
                            easing: 'easeInOutQuad'
                        });
                    }
                    
                    const message = 'Товар добавлен в корзину!'
                    
                    showCartNotification(message);
                    
                    setTimeout(() => {
                        this.textContent = originalText;
                        this.style.background = '';
                        this.classList.remove('loading');
                        this.disabled = false;
                    }, 200);
                    
                } else {
                    throw new Error(data.error || 'Ошибка добавления');
                }
                
            } catch (error) {
                console.error('Ошибка добавления:', error);
                this.textContent = 'Ошибка';
                this.style.background = '#dc3545';
                this.classList.remove('loading');
                
                showCartNotification(
                    error.message || 'Ошибка при добавлении', 
                    'error'
                );
                
                setTimeout(() => {
                    this.textContent = originalText;
                    this.style.background = originalBackground;
                    this.disabled = false;
                }, 3000);
            }
        });
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

    window.addEventListener('load', function() {
        AOS.init({
            duration: 800,
            once: true,
            offset: 100,
            startEvent: 'load',
            initClassName: 'aos-init',
            animatedClassName: 'aos-animate'
        });
        
        setTimeout(() => {
            AOS.refresh();
        }, 100);
    });

    const statsSection = document.querySelector('.hero-stats');
    if (statsSection) {
        observer.observe(statsSection);
    }

    const swiper = new Swiper('.swiper', {
        loop: true,
        slidesPerView: 1,
        spaceBetween: 25,
        centeredSlides: true,
        speed: 800,
        autoplay: {
            delay: 50000,
            disableOnInteraction: false,
            pauseOnMouseEnter: true,
        },
        pagination: {
            el: '.swiper-pagination',
            clickable: true,
            dynamicBullets: true,
        },
        navigation: {
            nextEl: '.swiper-button-next',
            prevEl: '.swiper-button-prev',
        },
        breakpoints: {
            640: {
                slidesPerView: 1,
                spaceBetween: 20,
            },
            768: {
                slidesPerView: 2,
                spaceBetween: 25,
                centeredSlides: false,
            },
            1024: {
                slidesPerView: 3,
                spaceBetween: 30,
                centeredSlides: true,
            },
            1280: {
                slidesPerView: 4,
                spaceBetween: 30,
                centeredSlides: false,
            }
        },
        on: {
            init: function() {
                updateProgressBar(this);
            },
            slideChange: function() {
                updateProgressBar(this);
            },
        }
    });

    function updateProgressBar(swiper) {
        const progress = document.querySelector('.swiper-progress');
        const total = swiper.slides.length - (swiper.params.loop ? 2 : 0);
        const current = swiper.realIndex;
        const progressWidth = ((current + 1) / total) * 100;
        progress.style.width = progressWidth + '%';
    }

    document.querySelectorAll('.service-card').forEach(card => {
        card.addEventListener('click', function() {
            const serviceName = this.querySelector('h3').textContent;
            anime({
                targets: this,
                scale: [1, 0.95, 1],
                duration: 300,
                easing: 'easeInOutQuad'
            });
            console.log(`Переход к услуге: ${serviceName}`);
        });
    });

    const cookieNotification = document.getElementById('cookie-notification');
    const acceptCookiesBtn = document.getElementById('accept-cookies');
    const settingsCookiesBtn = document.getElementById('settings-cookies');
    const cookieSettings = document.getElementById('cookie-settings');
    const closeSettingsBtn = document.getElementById('close-settings');
    const saveSettingsBtn = document.getElementById('save-settings');
    
    const COOKIES_ACCEPTED = 'cookiesAccepted';
    const COOKIE_SETTINGS = 'cookieSettings';
    
    function checkCookiesAccepted() {
        return localStorage.getItem(COOKIES_ACCEPTED) === 'true';
    }
    
    function getCookieSettings() {
        const settings = localStorage.getItem(COOKIE_SETTINGS);
        return settings ? JSON.parse(settings) : {
            necessary: true,
            analytical: true,
            functional: true
        };
    }
    
    function showCookieNotification() {
        if (!checkCookiesAccepted()) {
            setTimeout(() => {
                cookieNotification.classList.add('show');
            }, 2000); 
        }
    }
    
    function acceptAllCookies() {
        const settings = {
            necessary: true,
            analytical: true,
            functional: true
        };
        
        localStorage.setItem(COOKIES_ACCEPTED, 'true');
        localStorage.setItem(COOKIE_SETTINGS, JSON.stringify(settings));
        cookieNotification.classList.remove('show');
        
        initializeCookies(settings);
        showAcceptanceMessage('Все cookies приняты');
    }
    
    function saveCookieSettings() {
        const settings = {
            necessary: true,
            analytical: document.querySelector('input[name="analytical"]').checked,
            functional: document.querySelector('input[name="functional"]').checked
        };
        
        localStorage.setItem(COOKIES_ACCEPTED, 'true');
        localStorage.setItem(COOKIE_SETTINGS, JSON.stringify(settings));
        cookieNotification.classList.remove('show');
        cookieSettings.classList.remove('show');
        
        initializeCookies(settings);
        showAcceptanceMessage('Настройки cookies сохранены');
    }

    function initializeNecessaryCookies() {
        if (!localStorage.getItem('user_visit_id')) {
            const visitId = 'visit_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('user_visit_id', visitId);
        }
        
        try {
            localStorage.setItem('test', 'test');
            localStorage.removeItem('test');
        } catch (e) {
            console.error('LocalStorage недоступен:', e);
            document.cookie = "localstorage_unsupported=true; path=/; max-age=3600";
        }
    }

    function initializeAnalyticalCookies() {
        if (typeof ym !== 'undefined') {
            document.addEventListener('click', function(e) {
                if (e.target.matches('.btn, a, button')) {
                    const targetText = e.target.textContent.trim().substring(0, 50);
                    ym(105767211, 'reachGoal', 'button_click', { button: targetText });
                }
            });
            let scrollTracked = false;
            window.addEventListener('scroll', function() {
                if (window.scrollY > window.innerHeight * 0.5 && !scrollTracked) {
                    ym(105767211, 'reachGoal', 'scroll_50_percent');
                    scrollTracked = true;
                }
            });
        }
        if (typeof gtag !== 'undefined') {
            gtag('config', 'GTM-MWHF4HQX');
        }
        let pageLoadTime = Date.now();
        window.addEventListener('beforeunload', function() {
            const timeSpent = Date.now() - pageLoadTime;
            if (typeof ym !== 'undefined') {
                ym(105767211, 'params', { time_spent: Math.round(timeSpent / 1000) });
            }
        });
        const browserInfo = {
            screen: window.screen.width + 'x' + window.screen.height,
            language: navigator.language,
            online: navigator.onLine,
            userAgent: navigator.userAgent.substring(0, 100)
        };
        
        localStorage.setItem('analytics_browser_info', JSON.stringify(browserInfo));
    }

    function initializeFunctionalCookies() {
        const userSettings = getCookieSettings();
        if (localStorage.getItem('theme')) {
            document.documentElement.setAttribute('data-theme', localStorage.getItem('theme'));
        }
        const lastActiveSlide = localStorage.getItem('last_active_slide');
        if (lastActiveSlide && window.swiper) {
            setTimeout(() => {
                window.swiper.slideTo(parseInt(lastActiveSlide), 0);
            }, 100);
        }
        if (window.swiper) {
            swiper.on('slideChange', function() {
                localStorage.setItem('last_active_slide', this.activeIndex);
            });
        }
        if (performance.getEntriesByType('navigation').length > 0) {
            const navEntry = performance.getEntriesByType('navigation')[0];
            if (navEntry.type === 'navigate') {
                sessionStorage.setItem('last_page', window.location.pathname);
            }
        }
        
        const visitCount = parseInt(localStorage.getItem('visit_count') || '0') + 1;
        localStorage.setItem('visit_count', visitCount.toString());
        
        if (visitCount > 1) {
            const lastVisit = localStorage.getItem('last_visit');
            const now = new Date().toISOString();
            localStorage.setItem('last_visit', now);
            
            if (lastVisit) {
                const daysSinceLastVisit = Math.floor(
                    (new Date(now) - new Date(lastVisit)) / (1000 * 60 * 60 * 24)
                );
                
                if (daysSinceLastVisit > 7) {
                    console.log('Добро пожаловать обратно! Прошло дней:', daysSinceLastVisit);
                    
                    setTimeout(() => {
                        if (window.showCartNotification) {
                            showCartNotification('С возвращением! У нас появились новинки');
                        }
                    }, 3000);
                }
            }
        }
        
        const preferredView = localStorage.getItem('preferred_view');
        if (preferredView === 'compact') {
            document.body.classList.add('compact-view');
        }
        
        if (userSettings.functional && localStorage.getItem('form_autofill') === 'true') {
            const savedFormData = localStorage.getItem('contact_form_data');
            if (savedFormData && document.getElementById('contactForm')) {
                try {
                    const data = JSON.parse(savedFormData);
                    if (data.name && !document.getElementById('contactName').value) {
                        document.getElementById('contactName').value = data.name;
                    }
                } catch (e) {
                    console.error('Ошибка восстановления данных формы:', e);
                }
            }
            
            const formFields = document.querySelectorAll('#contactForm input, #contactForm textarea');
            formFields.forEach(field => {
                field.addEventListener('input', debounce(function() {
                    const formData = {};
                    formFields.forEach(f => {
                        if (f.name && f.value) {
                            formData[f.name] = f.value;
                        }
                    });
                    localStorage.setItem('contact_form_data', JSON.stringify(formData));
                }, 1000));
            });
        }
    }

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function safeLocalStorageSet(key, value) {
        try {
            localStorage.setItem(key, value);
            return true;
        } catch (e) {
            document.cookie = `${key}=${encodeURIComponent(value)}; path=/; max-age=2592000`;
            return false;
        }
    }
    
    function initializeCookies(settings) {
        
        initializeNecessaryCookies();
        
        if (settings.analytical) {
            initializeAnalyticalCookies();
        }
        
        if (settings.functional) {
            initializeFunctionalCookies();
        }
    }
    
    function showAcceptanceMessage(message) {
        console.log('✅ ' + message);
    }
    
    function loadSettingsToForm() {
        const settings = getCookieSettings();
        document.querySelector('input[name="analytical"]').checked = settings.analytical;
        document.querySelector('input[name="functional"]').checked = settings.functional;
    }
    
    if (acceptCookiesBtn) {
        acceptCookiesBtn.addEventListener('click', acceptAllCookies);
    }
    
    if (settingsCookiesBtn) {
        settingsCookiesBtn.addEventListener('click', function() {
            loadSettingsToForm();
            cookieSettings.classList.add('show');
        });
    }
    
    if (closeSettingsBtn) {
        closeSettingsBtn.addEventListener('click', function() {
            cookieSettings.classList.remove('show');
        });
    }
    
    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', saveCookieSettings);
    }
    
    showCookieNotification();
    
    if (checkCookiesAccepted()) {
        const settings = getCookieSettings();
        initializeCookies(settings);
    }

    const contactModal = document.getElementById('contactModal');
    const closeModal = document.querySelector('.close-modal');
    const contactForm = document.getElementById('contactForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn ? submitBtn.querySelector('.btn-text') : null;
    const btnLoading = submitBtn ? submitBtn.querySelector('.btn-loading') : null;
    
    const writeUsBtn = document.querySelector('.cta-buttons .btn-secondary');
    
    if (writeUsBtn) {
        writeUsBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (contactModal) {
                contactModal.style.display = 'block';
                document.body.style.overflow = 'hidden';
            }
        });
    } else {
        console.log('Кнопка "Написать нам" не найдена');
        const allButtons = document.querySelectorAll('.btn');
        allButtons.forEach(btn => {
            if (btn.textContent.includes('Написать нам')) {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    if (contactModal) {
                        contactModal.style.display = 'block';
                        document.body.style.overflow = 'hidden';
                    }
                });
            }
        });
    }
    
    if (closeModal) {
        closeModal.addEventListener('click', function() {
            if (contactModal) {
                contactModal.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        });
    }
    
    window.addEventListener('click', function(e) {
        if (e.target === contactModal) {
            contactModal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    });
    
    function validateForm() {
        let isValid = true;
        const name = document.getElementById('contactName').value.trim();
        const email = document.getElementById('contactEmail').value.trim();
        const phone = document.getElementById('contactPhone').value.trim();
        const message = document.getElementById('contactMessage').value.trim();
        
        document.querySelectorAll('.error-message').forEach(el => {
            el.style.display = 'none';
        });
        
        if (!name) {
            document.getElementById('nameError').textContent = 'Введите ваше имя';
            document.getElementById('nameError').style.display = 'block';
            isValid = false;
        }
        
        if (!email && !phone) {
            document.getElementById('emailError').textContent = 'Укажите email или телефон';
            document.getElementById('emailError').style.display = 'block';
            document.getElementById('phoneError').textContent = 'Укажите email или телефон';
            document.getElementById('phoneError').style.display = 'block';
            isValid = false;
        }
        
        if (email && !isValidEmail(email)) {
            document.getElementById('emailError').textContent = 'Введите корректный email';
            document.getElementById('emailError').style.display = 'block';
            isValid = false;
        }
        
        if (!message) {
            document.getElementById('messageError').textContent = 'Введите ваше сообщение';
            document.getElementById('messageError').style.display = 'block';
            isValid = false;
        }
        
        return isValid;
    }
    
    function isValidEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }
    
    if (contactForm) {
        contactForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (!validateForm()) return;
            
            const submitBtn = document.getElementById('submitBtn');
            if (submitBtn) {
                submitBtn.disabled = true;
                const originalText = submitBtn.textContent;
                submitBtn.textContent = 'Отправка...';
            }
            
            try {
                const formData = {
                    name: document.getElementById('contactName').value.trim(),
                    email: document.getElementById('contactEmail').value.trim(),
                    phone: document.getElementById('contactPhone').value.trim(),
                    message: document.getElementById('contactMessage').value.trim()
                };
                
                const response = await fetch('/contact/submit/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showMessage('success', data.message);
                    contactForm.reset();
                    setTimeout(() => {
                        if (contactModal) {
                            contactModal.style.display = 'none';
                            document.body.style.overflow = 'auto';
                        }
                    }, 2000);
                } else {
                    showMessage('error', data.error);
                }
                
            } catch (error) {
                console.error('Ошибка:', error);
                showMessage('error', 'Произошла ошибка при отправке. Попробуйте еще раз.');
            } finally {
                const submitBtn = document.getElementById('submitBtn');
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Отправить сообщение';
                }
            }
        });
    }
    
    function showMessage(type, text) {
        const oldMessages = document.querySelectorAll('.success-message, .error-message-global');
        oldMessages.forEach(msg => msg.remove());
        
        const messageDiv = document.createElement('div');
        messageDiv.className = type === 'success' ? 'success-message' : 'error-message-global';
        messageDiv.textContent = text;
        messageDiv.style.display = 'block';
        
        if (contactForm) {
            contactForm.insertBefore(messageDiv, contactForm.firstChild);
        }
        
        if (type === 'success') {
            setTimeout(() => {
                messageDiv.remove();
            }, 5000);
        }
    }
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && contactModal && contactModal.style.display === 'block') {
            contactModal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    });
});

document.querySelectorAll('[data-scroll]').forEach(link => {
    link.addEventListener('click', function(e) {
        e.preventDefault();
        const targetId = this.getAttribute('href');
        const targetElement = document.querySelector(targetId);
        
        if (targetElement) {
            const headerOffset = 100;
            const elementPosition = targetElement.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
            
            window.scrollTo({
                top: offsetPosition,
                behavior: 'smooth'
            });
        }
    });
});

function updateActiveNavLink() {
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-link-page');
    
    let currentSection = '';
    
    sections.forEach(section => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.clientHeight;
        if (window.scrollY >= (sectionTop - 150)) {
            currentSection = section.getAttribute('id');
        }
    });
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        const href = link.getAttribute('href').substring(1);
        if (href === currentSection) {
            link.classList.add('active');
        }
    });
}

window.addEventListener('scroll', updateActiveNavLink);

let lastScrollTop = 0;
const header = document.querySelector('.header');
const scrollThreshold = 50;

if (header) {
    window.addEventListener('scroll', function() {
        let scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        if (scrollTop > lastScrollTop && scrollTop > scrollThreshold) {
            header.classList.add('header-hidden');
        } else {
            header.classList.remove('header-hidden');
        }
        
        if (scrollTop > 50) {
            header.classList.add('header-scrolled');
        } else {
            header.classList.remove('header-scrolled');
        }
        
        lastScrollTop = scrollTop;
    });
}