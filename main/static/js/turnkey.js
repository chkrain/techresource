document.addEventListener('DOMContentLoaded', function() {
    // ========== 1. Toggle для проектов ==========
    const toggleBtns = document.querySelectorAll('.project-toggle-btn');
    
    toggleBtns.forEach((btn) => {
        btn.addEventListener('click', function() {
            const projectCard = this.closest('.project-card');
            const dropdown = projectCard.querySelector('.project-dropdown');
            
            projectCard.classList.toggle('active');
            
            const isActive = projectCard.classList.contains('active');
            const toggleText = this.querySelector('.toggle-text');
            toggleText.textContent = isActive ? 'Свернуть' : 'Подробнее о проекте';
            
            if (isActive) {
                setTimeout(() => {
                    dropdown.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'nearest' 
                    });
                    setTimeout(() => {
                        initProjectSliders();
                        attachZoomWithNavigation();
                        attachZoomForRegularImages();
                        attachGalleryZoomHandler();
                    }, 100);
                }, 300);
            }
        });
    });
    
    // ========== 2. Функция для открытия модального окна с навигацией ==========
    function openModalWithNavigation(clickedImg, allImages, startIndex) {
        const oldModal = document.querySelector('.image-modal-full');
        if (oldModal) oldModal.remove();
        
        let currentIndex = startIndex;
        
        const modal = document.createElement('div');
        modal.className = 'image-modal-full';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.95);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        
        const imgContainer = document.createElement('div');
        imgContainer.style.cssText = `
            position: relative;
            width: 100%;
            height: 85%;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        const modalImg = document.createElement('img');
        modalImg.src = allImages[currentIndex].src;
        modalImg.alt = allImages[currentIndex].alt;
        modalImg.style.cssText = `
            max-width: 90%;
            max-height: 90%;
            object-fit: contain;
            border-radius: 8px;
        `;
        
        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '✕';
        closeBtn.style.cssText = `
            position: absolute;
            top: 20px;
            right: 20px;
            background: white;
            border: none;
            width: 45px;
            height: 45px;
            border-radius: 50%;
            font-size: 24px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10001;
            transition: all 0.2s;
        `;
        closeBtn.onmouseover = () => closeBtn.style.transform = 'scale(1.1)';
        closeBtn.onmouseout = () => closeBtn.style.transform = 'scale(1)';
        
        const prevBtn = document.createElement('button');
        prevBtn.innerHTML = '‹';
        prevBtn.style.cssText = `
            position: absolute;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(255,255,255,0.8);
            border: none;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            font-size: 32px;
            cursor: pointer;
            display: ${allImages.length > 1 ? 'flex' : 'none'};
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
            z-index: 10001;
        `;
        
        const nextBtn = document.createElement('button');
        nextBtn.innerHTML = '›';
        nextBtn.style.cssText = `
            position: absolute;
            right: 20px;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(255,255,255,0.8);
            border: none;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            font-size: 32px;
            cursor: pointer;
            display: ${allImages.length > 1 ? 'flex' : 'none'};
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
            z-index: 10001;
        `;
        
        const counter = document.createElement('div');
        counter.style.cssText = `
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-family: monospace;
            z-index: 10001;
        `;
        counter.textContent = `${currentIndex + 1} / ${allImages.length}`;
        
        function updateImage(index) {
            if (index < 0) index = allImages.length - 1;
            if (index >= allImages.length) index = 0;
            currentIndex = index;
            modalImg.src = allImages[currentIndex].src;
            modalImg.alt = allImages[currentIndex].alt;
            counter.textContent = `${currentIndex + 1} / ${allImages.length}`;
        }
        
        prevBtn.onclick = (e) => {
            e.stopPropagation();
            updateImage(currentIndex - 1);
        };
        
        nextBtn.onclick = (e) => {
            e.stopPropagation();
            updateImage(currentIndex + 1);
        };
        
        function handleKeydown(e) {
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                updateImage(currentIndex - 1);
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                updateImage(currentIndex + 1);
            } else if (e.key === 'Escape') {
                closeModal();
            }
        }
        
        function closeModal() {
            modal.style.opacity = '0';
            setTimeout(() => {
                modal.remove();
                document.removeEventListener('keydown', handleKeydown);
            }, 300);
        }
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });
        
        closeBtn.onclick = (e) => {
            e.stopPropagation();
            closeModal();
        };
        
        imgContainer.appendChild(modalImg);
        if (allImages.length > 1) {
            imgContainer.appendChild(prevBtn);
            imgContainer.appendChild(nextBtn);
        }
        modal.appendChild(imgContainer);
        modal.appendChild(closeBtn);
        modal.appendChild(counter);
        document.body.appendChild(modal);
        
        setTimeout(() => modal.style.opacity = '1', 10);
        document.addEventListener('keydown', handleKeydown);
    }
    
    // ========== 3. Обработка кликов по изображениям в слайдере ==========
    function attachZoomWithNavigation() {
        const sliderImages = document.querySelectorAll('.project-swiper .swiper-slide img');
        sliderImages.forEach(img => {
            img.removeEventListener('click', zoomWithNavHandler);
            img.addEventListener('click', zoomWithNavHandler);
            img.style.cursor = 'pointer';
        });
    }
    
    function zoomWithNavHandler(e) {
        e.stopPropagation();
        const clickedImg = e.target;
        const swiperContainer = clickedImg.closest('.swiper');
        if (!swiperContainer) return;
        
        const allImages = [];
        const slides = swiperContainer.querySelectorAll('.swiper-slide img');
        let currentIndex = 0;
        
        slides.forEach((img, idx) => {
            allImages.push({
                src: img.src,
                alt: img.alt || 'Изображение'
            });
            if (img === clickedImg) currentIndex = idx;
        });
        
        if (allImages.length > 0) {
            openModalWithNavigation(clickedImg, allImages, currentIndex);
        }
    }
    
    // ========== 4. Обработка обычных zoomable изображений ==========
    function attachZoomForRegularImages() {
        const regularImages = document.querySelectorAll('.zoomable:not(.project-swiper .swiper-slide img):not(.stage-gallery .zoomable)');
        regularImages.forEach(img => {
            img.removeEventListener('click', regularZoomHandler);
            img.addEventListener('click', regularZoomHandler);
            img.style.cursor = 'pointer';
        });
    }
    
    function regularZoomHandler(e) {
        e.stopPropagation();
        const img = e.target;
        const allImages = [{ src: img.src, alt: img.alt || 'Изображение' }];
        openModalWithNavigation(img, allImages, 0);
    }
    
    // ========== 5. Обработка галерей (stage-gallery) ==========
    function attachGalleryZoomHandler() {
        const galleries = document.querySelectorAll('.stage-gallery');
        
        galleries.forEach(gallery => {
            const images = gallery.querySelectorAll('.zoomable');
            images.forEach(img => {
                img.removeEventListener('click', galleryZoomHandler);
                img.addEventListener('click', galleryZoomHandler);
                img.style.cursor = 'pointer';
            });
        });
    }
    
    function galleryZoomHandler(e) {
        e.stopPropagation();
        const clickedImg = e.target;
        const gallery = clickedImg.closest('.stage-gallery');
        if (!gallery) return;
        
        const allImages = [];
        const images = gallery.querySelectorAll('.zoomable');
        let currentIndex = 0;
        
        images.forEach((img, idx) => {
            allImages.push({
                src: img.src,
                alt: img.alt || 'Изображение'
            });
            if (img === clickedImg) currentIndex = idx;
        });
        
        if (allImages.length > 0) {
            openModalWithNavigation(clickedImg, allImages, currentIndex);
        }
    }
    
    // ========== 6. Клик по превью проекта ==========
    function attachPreviewClickHandler() {
        const projectCards = document.querySelectorAll('.project-card');
        projectCards.forEach(card => {
            const previewImage = card.querySelector('.project-image img');
            if (!previewImage) return;
            previewImage.removeEventListener('click', previewClickHandler);
            previewImage.addEventListener('click', previewClickHandler);
            previewImage.style.cursor = 'pointer';
        });
    }
    
    function previewClickHandler(e) {
        e.stopPropagation();
        const clickedImg = e.target;
        const projectCard = clickedImg.closest('.project-card');
        if (!projectCard) return;
        
        let allImages = [];
        
        // Ищем изображения в слайдере
        const swiperContainer = projectCard.querySelector('.swiper');
        if (swiperContainer) {
            const slides = swiperContainer.querySelectorAll('.swiper-slide img');
            slides.forEach(img => {
                allImages.push({
                    src: img.src,
                    alt: img.alt || 'Изображение'
                });
            });
        }
        
        // Если слайдера нет, ищем в обычных галереях
        if (allImages.length === 0) {
            const galleryImages = projectCard.querySelectorAll('.stage-gallery .zoomable');
            galleryImages.forEach(img => {
                if (!allImages.some(i => i.src === img.src)) {
                    allImages.push({
                        src: img.src,
                        alt: img.alt || 'Изображение'
                    });
                }
            });
        }
        
        // Добавляем превью, если его нет
        const previewSrc = clickedImg.src;
        if (!allImages.some(i => i.src === previewSrc)) {
            allImages.unshift({
                src: previewSrc,
                alt: clickedImg.alt || 'Превью проекта'
            });
        }
        
        let currentIndex = allImages.findIndex(i => i.src === previewSrc);
        if (currentIndex === -1) currentIndex = 0;
        
        if (allImages.length > 0) {
            openModalWithNavigation(clickedImg, allImages, currentIndex);
        }
    }
    
    // ========== 7. Инициализация Swiper слайдеров ==========
    function initProjectSliders() {
        const silosSwiper = document.getElementById('silosSwiper');
        if (silosSwiper && typeof Swiper !== 'undefined') {
            if (silosSwiper.swiper) silosSwiper.swiper.destroy(true, true);
            new Swiper(silosSwiper, {
                slidesPerView: 1,
                spaceBetween: 20,
                loop: true,
                autoplay: { delay: 4000, disableOnInteraction: false },
                navigation: { nextEl: '.swiper-button-next', prevEl: '.swiper-button-prev' },
                pagination: { el: '.swiper-pagination', clickable: true, dynamicBullets: true },
                breakpoints: { 640: { slidesPerView: 2 }, 1024: { slidesPerView: 3 } }
            });
        }
        
        const bsu2Swiper = document.getElementById('bsu2Swiper');
        if (bsu2Swiper && typeof Swiper !== 'undefined') {
            if (bsu2Swiper.swiper) bsu2Swiper.swiper.destroy(true, true);
            new Swiper(bsu2Swiper, {
                slidesPerView: 1,
                spaceBetween: 20,
                loop: true,
                autoplay: { delay: 4000, disableOnInteraction: false },
                navigation: { nextEl: '.swiper-button-next', prevEl: '.swiper-button-prev' },
                pagination: { el: '.swiper-pagination', clickable: true, dynamicBullets: true },
                breakpoints: { 640: { slidesPerView: 2 }, 1024: { slidesPerView: 3 } }
            });
        }
    }
    
    // ========== 8. Оптимизация AOS и ускорение отображения ==========
    function optimizeRendering() {
        // Показываем контент немедленно
        document.querySelectorAll('.project-stage, .project-card, .section-title, .section-subtitle').forEach(el => {
            if (el.style.opacity === '0') {
                el.style.opacity = '1';
                el.style.transform = 'translateY(0)';
            }
        });
        
        // Быстрая инициализация AOS
        if (typeof AOS !== 'undefined') {
            AOS.init({
                duration: 400,
                once: true,
                offset: 30,
                disable: window.innerWidth < 768
            });
        }
    }
    
    // ========== 9. Анимация появления этапов (отключаем для скорости) ==========
    // Заменяем IntersectionObserver на простое появление
    document.querySelectorAll('.project-stage').forEach((stage, index) => {
        stage.style.opacity = '1';
        stage.style.transform = 'translateY(0)';
    });
    
    // ========== 10. Запуск ==========
    // Сначала показываем контент
    optimizeRendering();
    
    // Затем инициализируем слайдеры и обработчики
    initProjectSliders();
    
    setTimeout(() => {
        attachZoomWithNavigation();
        attachZoomForRegularImages();
        attachPreviewClickHandler();
        attachGalleryZoomHandler();
    }, 100);
});