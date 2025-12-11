document.addEventListener('DOMContentLoaded', function() {
    // 1. Анимация счетчиков
    initCounters();
    
    // 2. Управление FAQ
    initFAQ();
    
    // 3. Управление разворачиванием проектов
    initProjectToggles();
    
    // 4. Плавная прокрутка
    initSmoothScroll();
    
    // 5. Показать уведомление о скачивании
    initDownloadNotifications();
});

function initCounters() {
    if (!('IntersectionObserver' in window)) {
        document.querySelectorAll('.stat-number').forEach(counter => {
            counter.textContent = counter.getAttribute('data-count');
        });
        return;
    }

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
            
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const currentValue = Math.floor(startValue + (target - startValue) * easeOutQuart);
            
            element.textContent = currentValue;
            
            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            } else {
                element.textContent = target;
            }
        }
        
        requestAnimationFrame(updateCounter);
    }
    
    const statsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !countersAnimated) {
                statNumbers.forEach(animateCounter);
                countersAnimated = true;
                statsObserver.disconnect();
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
}

function initFAQ() {
    const faqItems = document.querySelectorAll('.faq-item');
    
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        const answer = item.querySelector('.faq-answer');
        const toggle = item.querySelector('.faq-toggle');
        
        if (!question || !answer) return;
        
        question.setAttribute('aria-expanded', 'false');
        question.setAttribute('role', 'button');
        question.setAttribute('tabindex', '0');
        answer.setAttribute('aria-hidden', 'true');
        
        function toggleFAQ() {
            const isActive = item.classList.contains('active');
            
            if (!isActive) {
                // Закрываем все остальные
                faqItems.forEach(faqItem => {
                    const faqAnswer = faqItem.querySelector('.faq-answer');
                    const faqToggle = faqItem.querySelector('.faq-toggle');
                    const faqQuestion = faqItem.querySelector('.faq-question');
                    
                    if (faqAnswer && faqQuestion) {
                        faqItem.classList.remove('active');
                        faqAnswer.style.maxHeight = null;
                        if (faqToggle) faqToggle.textContent = '+';
                        faqQuestion.setAttribute('aria-expanded', 'false');
                        faqAnswer.setAttribute('aria-hidden', 'true');
                    }
                });
                
                // Открываем текущий
                item.classList.add('active');
                answer.style.maxHeight = answer.scrollHeight + 'px';
                if (toggle) toggle.textContent = '−';
                question.setAttribute('aria-expanded', 'true');
                answer.setAttribute('aria-hidden', 'false');
            } else {
                // Закрываем текущий
                item.classList.remove('active');
                answer.style.maxHeight = null;
                if (toggle) toggle.textContent = '+';
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
}

function initProjectToggles() {
    document.querySelectorAll('.toggle-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const caseCard = this.closest('.case-card');
            const detailsSection = caseCard.querySelector('.case-details-expanded');
            const toggleIcon = this.querySelector('.toggle-icon');
            const toggleText = this.querySelector('.toggle-text');
            
            const isExpanded = detailsSection.classList.contains('active');
            
            if (isExpanded) {
                // Сворачиваем
                detailsSection.classList.remove('active');
                this.classList.remove('expanded');
                toggleText.textContent = 'Подробнее о проекте';
                toggleIcon.textContent = '▼';
            } else {
                // Разворачиваем
                detailsSection.classList.add('active');
                this.classList.add('expanded');
                toggleText.textContent = 'Свернуть детали';
                toggleIcon.textContent = '▲';
                
                // Плавная прокрутка к деталям
                setTimeout(() => {
                    const topOffset = detailsSection.getBoundingClientRect().top + window.pageYOffset - 80;
                    window.scrollTo({
                        top: topOffset,
                        behavior: 'smooth'
                    });
                }, 100);
            }
        });
    });
}

function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            
            if (targetId === '#' || targetId === '#contact') {
                return;
            }
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                e.preventDefault();
                
                const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset - 80;
                const startPosition = window.pageYOffset;
                const distance = targetPosition - startPosition;
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
}

function initDownloadNotifications() {
    // Можно добавить простое уведомление о начале скачивания
    document.querySelectorAll('.document-item').forEach(link => {
        link.addEventListener('click', function(e) {
            const fileName = this.download || this.href.split('/').pop();
            console.log(`Начинается скачивание: ${fileName}`);
            
            // Можно добавить аналитику здесь
            if (typeof ym !== 'undefined') {
                ym(105767211, 'reachGoal', 'document_download', {
                    filename: fileName
                });
            }
        });
    });
}

// Глобальная обработка ошибок
window.addEventListener('error', function(e) {
    console.error('Error in services.js:', e.error);
});

// Отключение анимаций при prefers-reduced-motion
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.documentElement.style.setProperty('--transition', 'none');
}