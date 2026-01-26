function toggleMenu() {
    const nav = document.getElementById("main-nav");
    if (nav) {
        console.log('Toggle menu called from services.js');
        nav.classList.toggle('active');
        const menuBtn = document.querySelector('.mobile-menu-btn');
        if (menuBtn) {
            const isExpanded = nav.classList.contains('active');
            menuBtn.setAttribute('aria-expanded', isExpanded);
        }
        if (nav.classList.contains('active')) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    initCounters();
    initFAQ();
    initProjectToggles();
    initSmoothScroll();
    initDownloadNotifications();
    initProjectsGallery();
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
        answer.setAttribute('aria-hidden', 'true');
        answer.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
        
        function toggleFAQ() {
            const isActive = item.classList.contains('active');
            
            if (!isActive) {
                faqItems.forEach(otherItem => {
                    if (otherItem !== item && otherItem.classList.contains('active')) {
                        const otherAnswer = otherItem.querySelector('.faq-answer');
                        const otherToggle = otherItem.querySelector('.faq-toggle');
                        
                        otherItem.classList.remove('active');
                        otherAnswer.style.maxHeight = '0';
                        otherAnswer.style.opacity = '0';
                        if (otherToggle) otherToggle.textContent = '+';
                        otherItem.querySelector('.faq-question').setAttribute('aria-expanded', 'false');
                        otherAnswer.setAttribute('aria-hidden', 'true');
                    }
                });
                
                item.classList.add('active');
                answer.style.maxHeight = answer.scrollHeight + 'px';
                answer.style.opacity = '1';
                answer.style.paddingBottom = '20px';
                
                if (toggle) {
                    toggle.style.transform = 'rotate(45deg)';
                    toggle.textContent = '−';
                }
                
                question.setAttribute('aria-expanded', 'true');
                answer.setAttribute('aria-hidden', 'false');
                
            } else {
                item.classList.remove('active');
                answer.style.maxHeight = '0';
                answer.style.opacity = '0';
                answer.style.paddingBottom = '0';
                
                if (toggle) {
                    toggle.style.transform = 'rotate(0deg)';
                    toggle.textContent = '+';
                }
                
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
        
        question.addEventListener('mouseenter', () => {
            if (!item.classList.contains('active')) {
                question.style.transform = 'translateX(5px)';
            }
        });
        
        question.addEventListener('mouseleave', () => {
            question.style.transform = 'translateX(0)';
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
                detailsSection.classList.remove('active');
                this.classList.remove('expanded');
                toggleText.textContent = 'Подробнее о проекте';
                toggleIcon.textContent = '▼';
            } else {
                detailsSection.classList.add('active');
                this.classList.add('expanded');
                toggleText.textContent = 'Свернуть детали';
                toggleIcon.textContent = '▲';
                
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
    document.querySelectorAll('.document-item').forEach(link => {
        link.addEventListener('click', function(e) {
            const fileName = this.download || this.href.split('/').pop();
            console.log(`Начинается скачивание: ${fileName}`);
            
            if (typeof ym !== 'undefined') {
                ym(105767211, 'reachGoal', 'document_download', {
                    filename: fileName
                });
            }
        });
    });
}

function initProjectsGallery() {
    const projectsData = {
        1: {
            id: 1,
            title: "Автоматизированная система управления технологией производства",
            subtitle: "Мониторинг промышленного оборудования",
            image: "/static/images/img/grafana2sca.jpg",
            description: "Разработка современной системы для мониторинга промышленного оборудования с использованием Grafana. Система позволяет отслеживать параметры оборудования в реальном времени, генерировать отчеты и настраивать уведомления.",
            details: [
                { icon: "📊", label: "Производительность", value: "Увеличена на 40%" },
                { icon: "💰", label: "Экономия", value: "до 25%" },
                { icon: "⏱️", label: "Срок разработки", value: "2 месяца" },
                { icon: "🏭", label: "Тип проекта", value: "Промышленная SCADA" }
            ],
            features: [
                "Реальный мониторинг параметров",
                "Автоматическая генерация отчетов",
                "Мобильный доступ к данным",
                "Интеграция с PLC контроллерами",
                "Настраиваемые дашборды",
                "Система оповещений"
            ],
            techTags: ["Grafana", "SCADA", "Промышленность", "Мониторинг", "Дашборды"],
            gallery: [
                "/static/images/img/grafanasca.jpg",
                "/static/images/img/grafanatrepelsca.jpg"
            ]
        },
        2: {
            id: 2,
            title: "Автоматизация для покраски фанеры",
            subtitle: "Управление линией покраски торцов",
            image: "/static/images/img/porsca.jpg",
            description: "Система управления линией покраски торцов фанеры с визуализацией технологического процесса и мониторингом параметров оборудования.",
            details: [
                { icon: "📈", label: "Производительность", value: "+35%" },
                { icon: "🎯", label: "Качество", value: "Брак -22%" },
                { icon: "⚡", label: "Экономия энергии", value: "15%" },
                { icon: "🔄", label: "Автоматизация", value: "95%" }
            ],
            features: [
                "Визуализация процесса покраски",
                "Управление конвейерными линиями",
                "Мониторинг температуры и влажности",
                "Автоматическое дозирование краски",
                "Система безопасности и аварийных остановок"
            ],
            techTags: ["Siemens", "SCADA", "Деревообработка", "Автоматизация"],
            gallery: []
        },
        3: {
            id: 3,
            title: "Автоматизация для переработки трепела",
            subtitle: "Система управления технологическим процессом",
            image: "/static/images/img/trepelsca.jpg",
            description: "Система управления процессом переработки трепела с автоматическим дозированием компонентов и контролем качества продукции.",
            details: [
                { icon: "⚖️", label: "Точность дозирования", value: "±0.5%" },
                { icon: "📊", label: "Производительность", value: "+30%" },
                { icon: "🔄", label: "Автоматизация", value: "90%" },
                { icon: "🏗️", label: "Масштаб", value: "Промышленный" }
            ],
            features: [
                "Автоматическое дозирование компонентов",
                "Контроль качества продукции",
                "Мониторинг оборудования",
                "Генерация производственных отчетов",
                "Удаленный доступ к системе"
            ],
            techTags: ["Трепел", "Дозирование", "Производство", "SCADA"],
            gallery: []
        },
        4: {
            id: 4,
            title: "Автоматизация для буссера",
            subtitle: "Система управления буссером",
            image: "/static/images/img/bsusca.jpg",
            description: "Система управления буссером с мониторингом параметров и системой аварийных остановок для обеспечения безопасности процесса.",
            details: [
                { icon: "🛡️", label: "Безопасность", value: "Уровень 4" },
                { icon: "📈", label: "Эффективность", value: "+25%" },
                { icon: "⚡", label: "Надежность", value: "99.8%" },
                { icon: "🔧", label: "Контроллер", value: "Siemens S7-1500" }
            ],
            features: [
                "Система аварийных остановок",
                "Мониторинг давления и температуры",
                "Защита от перегрузок",
                "Дистанционное управление",
                "Журналирование событий"
            ],
            techTags: ["Буссер", "Безопасность", "ПЛК", "Автоматизация"],
            gallery: []
        },
        5: {
            id: 5,
            title: "Автоматизация для гипсового производства",
            subtitle: "Управление производственной линией",
            image: "/static/images/img/gipsca.jpg",
            description: "Система управления производственной линией гипса с контролем температуры, влажности и автоматическим регулированием процесса.",
            details: [
                { icon: "🌡️", label: "Точность контроля", value: "±1°C" },
                { icon: "📊", label: "Стабильность", value: "95%" },
                { icon: "💰", label: "Экономия", value: "18%" },
                { icon: "⚡", label: "Энергоэффективность", value: "+20%" }
            ],
            features: [
                "Контроль температуры и влажности",
                "Автоматическое регулирование процесса",
                "Оптимизация энергопотребления",
                "Контроль качества продукции",
                "Интеграция с КИПиА"
            ],
            techTags: ["Гипс", "Производство", "КИПиА", "Температура"],
            gallery: []
        },
        6: {
            id: 6,
            title: "Автоматизация для производства каучука",
            subtitle: "Управление химическим процессом",
            image: "/static/images/img/kauchsca.jpg",
            description: "Система управления процессом производства синтетического каучука с контролем реакторов и параметров реакции.",
            details: [
                { icon: "🧪", label: "Точность процесса", value: "99.5%" },
                { icon: "📈", label: "Выход продукта", value: "+15%" },
                { icon: "⚡", label: "Безопасность", value: "Уровень SIL 2" },
                { icon: "💰", label: "Экономия сырья", value: "12%" }
            ],
            features: [
                "Контроль химических реакторов",
                "Мониторинг давления и температуры",
                "Автоматическое дозирование реагентов",
                "Система безопасности процессов",
                "Контроль качества продукции"
            ],
            techTags: ["Каучук", "Химия", "Реакторы", "Безопасность"],
            gallery: []
        },
        7: {
            id: 7,
            title: "Автоматизация для обогащения песка",
            subtitle: "Система управления процессом обогащения",
            image: "/static/images/img/pesoksca.jpg",
            description: "Система управления процессом обогащения песка с автоматическим контролем качества и оптимизацией процесса.",
            details: [
                { icon: "⭐", label: "Качество продукта", value: "+28%" },
                { icon: "📊", label: "Производительность", value: "+32%" },
                { icon: "⚡", label: "Энергопотребление", value: "-18%" },
                { icon: "🔄", label: "Автоматизация", value: "88%" }
            ],
            features: [
                "Автоматический контроль качества",
                "Оптимизация процесса обогащения",
                "Мониторинг оборудования",
                "Энергоэффективное управление",
                "Система отчетности"
            ],
            techTags: ["Песок", "Обогащение", "Качество", "Оптимизация"],
            gallery: []
        },
        8: {
            id: 8,
            title: "Автоматизация для линии тука",
            subtitle: "Управление производственной линией",
            image: "/static/images/img/tuksca.jpg",
            description: "Система управления технологической линией производства тука с автоматизацией процесса и системой отчетности.",
            details: [
                { icon: "📊", label: "Производительность", value: "+40%" },
                { icon: "💰", label: "Экономия", value: "22%" },
                { icon: "📈", label: "Качество", value: "Брак -15%" },
                { icon: "⚡", label: "Надежность", value: "99.9%" }
            ],
            features: [
                "Автоматизация технологического процесса",
                "Система отчетности в реальном времени",
                "Контроль качества продукции",
                "Мониторинг оборудования",
                "Удаленный доступ к данным"
            ],
            techTags: ["Тук", "Производство", "Отчетность", "Автоматизация"],
            gallery: []
        },
        9: {
            id: 9,
            title: "Автоматизация для УДО",
            subtitle: "Управление установкой депарафинизации",
            image: "/static/images/img/udosca.jpg",
            description: "Система управления установкой депарафинизации и обезвоживания для нефтеперерабатывающей промышленности.",
            details: [
                { icon: "🛢️", label: "Эффективность", value: "+25%" },
                { icon: "⚡", label: "Энергосбережение", value: "17%" },
                { icon: "🎯", label: "Качество", value: "Соответствие ГОСТ" },
                { icon: "🛡️", label: "Безопасность", value: "ATEX зона 2" }
            ],
            features: [
                "Управление процессом депарафинизации",
                "Контроль температуры и давления",
                "Система безопасности для взрывоопасных зон",
                "Интеграция с АСУ ТП",
                "Мониторинг энергопотребления"
            ],
            techTags: ["УДО", "Нефтепереработка", "Безопасность", "Автоматика"],
            gallery: []
        },
        10: {
            id: 10,
            title: "ПО для фасовки трепела",
            subtitle: "Управление линией фасовки и упаковки",
            image: "/static/images/img/trepel2sca.jpg",
            description: "Система управления линией фасовки и упаковки трепела с контролем веса и автоматической маркировкой.",
            details: [
                { icon: "⚖️", label: "Точность фасовки", value: "±10г" },
                { icon: "📊", label: "Скорость", value: "1200 ед/час" },
                { icon: "💰", label: "Экономия", value: "20%" },
                { icon: "🔄", label: "Автоматизация", value: "92%" }
            ],
            features: [
                "Автоматическая фасовка по весу",
                "Контроль качества упаковки",
                "Маркировка продукции",
                "Сортировка и паллетирование",
                "Отслеживание партий"
            ],
            techTags: ["Трепел", "Фасовка", "Упаковка", "Автоматизация"],
            gallery: []
        },
        11: {
            id: 11,
            title: "Grafana для трепела",
            subtitle: "Дашборды мониторинга процесса",
            image: "/static/images/img/grafanatrepelsca.jpg",
            description: "Разработка дашбордов Grafana для мониторинга процесса переработки трепела с аналитикой в реальном времени.",
            details: [
                { icon: "📊", label: "Визуализация", value: "15+ дашбордов" },
                { icon: "⚡", label: "Обновление", value: "1 секунда" },
                { icon: "📈", label: "Аналитика", value: "10+ метрик" },
                { icon: "🌐", label: "Доступ", value: "Web/Mobile" }
            ],
            features: [
                "Дашборды в реальном времени",
                "Исторический анализ данных",
                "Кастомные метрики и алерты",
                "Мобильная адаптация",
                "Экспорт отчетов"
            ],
            techTags: ["Grafana", "Трепел", "Аналитика", "Дашборды"],
            gallery: []
        },
        12: {
            id: 12,
            title: "Универсальный вид графиков",
            subtitle: "Многофункциональная система",
            image: "/static/images/img/grafanasca.jpg",
            description: "Разработка универсальной системы на базе Grafana для различных отраслей промышленности с модульной архитектурой.",
            details: [
                { icon: "🔄", label: "Модульность", value: "10+ модулей" },
                { icon: "🌐", label: "Поддержка", value: "Все браузеры" },
                { icon: "⚡", label: "Производительность", value: "10000 тэгов" },
                { icon: "🏭", label: "Отрасли", value: "5+ отраслей" }
            ],
            features: [
                "Модульная архитектура",
                "Поддержка всех промышленных протоколов",
                "Масштабируемость",
                "Кроссплатформенность",
                "Глубокая кастомизация"
            ],
            techTags: ["Grafana", "Универсальная", "Кроссплатформенность"],
            gallery: []
        }
    };

    const photoCards = document.querySelectorAll('.photo-card');
    const detailPanel = document.getElementById('projectDetailPanel');
    const panelOverlay = document.getElementById('panelOverlay');
    const closeButtons = document.querySelectorAll('.close-panel-btn, .close-bottom-btn');

    function openProjectPanel(projectId) {
        const project = projectsData[projectId];
        if (!project) return;

        const panelTitle = document.getElementById('panelTitle');
        const panelSubtitle = document.getElementById('panelSubtitle');
        const panelMainImage = document.getElementById('panelMainImage');
        const projectDescription = document.getElementById('projectDescription');
        const detailsContainer = document.getElementById('projectDetails');
        const featuresContainer = document.getElementById('projectFeatures');
        const tagsContainer = document.getElementById('panelTechTags');
        const galleryContainer = document.getElementById('photoGallery');

        if (panelTitle) panelTitle.textContent = project.title;
        if (panelSubtitle) panelSubtitle.textContent = project.subtitle;
        if (panelMainImage) {
            panelMainImage.src = project.image;
            panelMainImage.alt = project.title;
        }
        if (projectDescription) projectDescription.textContent = project.description;

        if (detailsContainer) {
            detailsContainer.innerHTML = project.details.map(detail => `
                <div class="detail-card">
                    <div class="detail-icon">${detail.icon}</div>
                    <div class="detail-label">${detail.label}</div>
                    <div class="detail-value">${detail.value}</div>
                </div>
            `).join('');
        }

        if (featuresContainer) {
            featuresContainer.innerHTML = project.features.map(feature => `
                <div class="feature-item">
                    <div class="feature-icon">✅</div>
                    <div class="feature-text">${feature}</div>
                </div>
            `).join('');
        }

        if (tagsContainer) {
            tagsContainer.innerHTML = project.techTags.map(tag => `
                <span class="panel-tech-tag">${tag}</span>
            `).join('');
        }

        if (galleryContainer) {
            if (project.gallery && project.gallery.length > 0) {
                galleryContainer.innerHTML = `
                    <h3 class="gallery-title">Дополнительные фотографии</h3>
                    <div class="photo-thumbnails">
                        ${project.gallery.map((img, index) => `
                            <div class="thumbnail" data-img-src="${img}">
                                <img src="${img}" alt="Фото проекта ${index + 1}" loading="lazy">
                                <div class="thumbnail-overlay">
                                    <span class="zoom-icon">🔍</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
                
                galleryContainer.querySelectorAll('.thumbnail').forEach(thumb => {
                    thumb.addEventListener('click', function() {
                        const imgSrc = this.getAttribute('data-img-src');
                        changeMainImage(imgSrc);
                    });
                });
            } else {
                galleryContainer.innerHTML = '';
            }
        }

        if (detailPanel) detailPanel.classList.add('active');
        if (panelOverlay) panelOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
        
        if (detailPanel) detailPanel.scrollTop = 0;
    }

    function closeProjectPanel() {
        const detailPanel = document.getElementById('projectDetailPanel');
        const panelOverlay = document.getElementById('panelOverlay');
        
        if (detailPanel) detailPanel.classList.remove('active');
        if (panelOverlay) panelOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    function changeMainImage(imgSrc) {
        const mainImg = document.getElementById('panelMainImage');
        if (!mainImg) return;
        
        document.querySelectorAll('.thumbnail').forEach(thumb => {
            thumb.classList.remove('active');
        });
        
        const activeThumb = document.querySelector(`.thumbnail[data-img-src="${imgSrc}"]`);
        if (activeThumb) activeThumb.classList.add('active');
        
        mainImg.style.opacity = '0.7';
        
        setTimeout(() => {
            mainImg.src = imgSrc;
            mainImg.style.opacity = '1';
        }, 200);
    }

    window.changeMainImage = changeMainImage;

    photoCards.forEach(card => {
        card.addEventListener('click', function() {
            const projectId = this.dataset.projectId;
            openProjectPanel(projectId);
        });
        
        card.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                const projectId = this.dataset.projectId;
                openProjectPanel(projectId);
            }
        });
        
        card.setAttribute('tabindex', '0');
        card.setAttribute('role', 'button');
    });

    closeButtons.forEach(btn => {
        btn.addEventListener('click', closeProjectPanel);
    });

    if (panelOverlay) {
        panelOverlay.addEventListener('click', closeProjectPanel);
    }

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && detailPanel && detailPanel.classList.contains('active')) {
            closeProjectPanel();
        }
    });

    photoCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            const projectId = this.dataset.projectId;
            const project = projectsData[projectId];
            if (project) {
                const img = new Image();
                img.src = project.image;
                
                project.gallery?.forEach(imgSrc => {
                    const galleryImg = new Image();
                    galleryImg.src = imgSrc;
                });
            }
        });
    });
}