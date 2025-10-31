// services.js - улучшенная версия
document.addEventListener('DOMContentLoaded', function() {
    // Проверка поддержки Intersection Observer
    if (!('IntersectionObserver' in window)) {
        // Фолбэк для старых браузеров
        document.querySelectorAll('.stat-number').forEach(counter => {
            counter.textContent = counter.getAttribute('data-count');
        });
        return;
    }

    // Анимация счетчиков с улучшенной логикой
    const statNumbers = document.querySelectorAll('.stat-number');
    let countersAnimated = false;
    
    function animateCounter(element) {
        const target = parseInt(element.getAttribute('data-count'));
        const duration = 2000;
        const startTime = performance.now();
        const startValue = 0;
        
        function updateCounter(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // easing function для более плавной анимации
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const currentValue = Math.floor(startValue + (target - startValue) * easeOutQuart);
            
            element.textContent = currentValue;
            
            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            } else {
                element.textContent = target; // Гарантируем точное значение
            }
        }
        
        requestAnimationFrame(updateCounter);
    }
    
    // Оптимизированный Intersection Observer
    const statsObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !countersAnimated) {
                statNumbers.forEach(animateCounter);
                countersAnimated = true;
                observer.disconnect();
            }
        });
    }, {
        threshold: 0.3,
        rootMargin: '0px 0px -50px 0px'
    });
    
    const statsSection = document.querySelector('.stats-section');
    if (statsSection) {
        statsObserver.observe(statsSection);
    }

    // Модальное окно - улучшенная версия
    const caseButtons = document.querySelectorAll('.case-more-btn');
    const modal = document.getElementById('caseModal');
    const modalBody = document.getElementById('modalBody');
    const modalClose = document.querySelector('.modal-close');
    
    // Данные для модальных окон
    const caseData = {
        1: {
            title: 'Автоматизация производственной линии',
            description: 'Проектирование системы автоматизации для пищевого производства',
            details: {
                'Срок': '45 дней',
                'Бюджет': '2.5 млн ₽',
                'Экономия': '12%',
                'Задача': 'Автоматизация процесса упаковки продукции',
                'Решение': 'Разработана система на базе ПЛК Siemens с интеграцией в ERP-систему',
                'Результат': 'Увеличение производительности на 25%, снижение брака на 15%'
            }
        },
        2: {
            title: 'Электроснабжение завода',
            description: 'Проект реконструкции системы электроснабжения промышленного предприятия',
            details: {
                'Срок': '60 дней',
                'Бюджет': '4.8 млн ₽',
                'Экономия': '15%',
                'Задача': 'Модернизация устаревшей системы электроснабжения',
                'Решение': 'Разработана новая схема с резервным питанием и системой мониторинга',
                'Результат': 'Повышение надежности на 40%, снижение потерь электроэнергии'
            }
        },
        3: {
            title: 'Система микроклимата',
            description: 'Проектирование климатических систем для фармацевтического производства',
            details: {
                'Срок': '30 дней',
                'Бюджет': '1.9 млн ₽',
                'Экономия': '18%',
                'Задача': 'Обеспечение стабильных параметров микроклимата в чистых помещениях',
                'Решение': 'Разработана система с многоступенчатой фильтрацией и точным контролем параметров',
                'Результат': 'Соответствие требованиям GMP, стабильные параметры температуры и влажности'
            }
        }
    };
    
    // Управление фокусом для доступности
    let focusedElementBeforeModal;
    
    function openModal(caseId) {
        const data = caseData[caseId];
        if (!data) return;
        
        focusedElementBeforeModal = document.activeElement;
        
        let modalContent = `
            <h2 id="modalTitle">${data.title}</h2>
            <p class="modal-description">${data.description}</p>
            <div class="modal-details">
        `;
        
        for (const [key, value] of Object.entries(data.details)) {
            modalContent += `
                <div class="modal-detail-item">
                    <span class="modal-detail-label">${key}:</span>
                    <span class="modal-detail-value">${value}</span>
                </div>
            `;
        }
        
        modalContent += `</div>`;
        modalBody.innerHTML = modalContent;
        
        // Показываем модальное окно
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        modal.setAttribute('aria-hidden', 'false');
        
        // Фокусируемся на модальном окне
        modal.focus();
        
        // Добавляем обработчики для клавиатуры
        document.addEventListener('keydown', handleModalKeydown);
        
        // Предотвращаем скролл body
        document.body.style.paddingRight = window.innerWidth - document.documentElement.clientWidth + 'px';
        document.body.style.overflow = 'hidden';
    }
    
    function closeModal() {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        document.body.style.paddingRight = '';
        modal.setAttribute('aria-hidden', 'true');
        
        // Возвращаем фокус
        if (focusedElementBeforeModal) {
            focusedElementBeforeModal.focus();
        }
        
        // Убираем обработчики
        document.removeEventListener('keydown', handleModalKeydown);
    }
    
    function handleModalKeydown(e) {
        if (e.key === 'Escape') {
            closeModal();
        }
        
        // Ловим фокус внутри модального окна
        if (e.key === 'Tab' && modal.style.display === 'flex') {
            const focusableElements = modal.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];
            
            if (e.shiftKey && document.activeElement === firstElement) {
                e.preventDefault();
                lastElement.focus();
            } else if (!e.shiftKey && document.activeElement === lastElement) {
                e.preventDefault();
                firstElement.focus();
            }
        }
    }
    
    // Обработчики для модального окна
    caseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const caseId = this.getAttribute('data-case');
            openModal(caseId);
        });
        
        // Добавляем поддержку клавиатуры для кнопок
        button.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                const caseId = this.getAttribute('data-case');
                openModal(caseId);
            }
        });
    });
    
    modalClose.addEventListener('click', closeModal);
    modalClose.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            closeModal();
        }
    });
    
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });
    
    // FAQ аккордеон с улучшенной доступностью
    const faqItems = document.querySelectorAll('.faq-item');
    
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        const answer = item.querySelector('.faq-answer');
        const toggle = item.querySelector('.faq-toggle');
        
        // Устанавливаем начальные ARIA-атрибуты
        question.setAttribute('aria-expanded', 'false');
        question.setAttribute('role', 'button');
        question.setAttribute('tabindex', '0');
        answer.setAttribute('aria-hidden', 'true');
        
        function toggleFAQ() {
            const isActive = item.classList.contains('active');
            
            if (!isActive) {
                // Закрываем все открытые элементы
                faqItems.forEach(faqItem => {
                    faqItem.classList.remove('active');
                    const faqAnswer = faqItem.querySelector('.faq-answer');
                    const faqToggle = faqItem.querySelector('.faq-toggle');
                    const faqQuestion = faqItem.querySelector('.faq-question');
                    
                    faqAnswer.style.maxHeight = null;
                    faqToggle.textContent = '+';
                    faqQuestion.setAttribute('aria-expanded', 'false');
                    faqAnswer.setAttribute('aria-hidden', 'true');
                });
                
                // Открываем текущий
                item.classList.add('active');
                answer.style.maxHeight = answer.scrollHeight + 'px';
                toggle.textContent = '−';
                question.setAttribute('aria-expanded', 'true');
                answer.setAttribute('aria-hidden', 'false');
            } else {
                // Закрываем текущий
                item.classList.remove('active');
                answer.style.maxHeight = null;
                toggle.textContent = '+';
                question.setAttribute('aria-expanded', 'false');
                answer.setAttribute('aria-hidden', 'true');
            }
        }
        
        question.addEventListener('click', toggleFAQ);
        question.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggleFAQ();
            }
        });
    });
    
    // Улучшенная плавная прокрутка
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            
            if (targetId === '#' || targetId === '#contact') {
                e.preventDefault();
                return;
            }
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                e.preventDefault();
                
                const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset;
                const startPosition = window.pageYOffset;
                const distance = targetPosition - startPosition - 100; // Отступ 100px
                const duration = 1000;
                let startTime = null;
                
                function animation(currentTime) {
                    if (startTime === null) startTime = currentTime;
                    const timeElapsed = currentTime - startTime;
                    const run = easeInOutQuad(timeElapsed, startPosition, distance, duration);
                    
                    window.scrollTo(0, run);
                    
                    if (timeElapsed < duration) {
                        requestAnimationFrame(animation);
                    }
                }
                
                function easeInOutQuad(t, b, c, d) {
                    t /= d/2;
                    if (t < 1) return c/2*t*t + b;
                    t--;
                    return -c/2 * (t*(t-2) - 1) + b;
                }
                
                requestAnimationFrame(animation);
            }
        });
    });
    
    // Добавляем обработку ошибок
    window.addEventListener('error', function(e) {
        console.error('Error in services.js:', e.error);
    });
    
    // Предотвращаем загрузку ненужных ресурсов если пользователь предпочитает reduced motion
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        // Отключаем сложные анимации
        document.documentElement.style.setProperty('--transition', 'none');
    }
});