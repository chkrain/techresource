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

    anime({
        targets: '.services-container',
        opacity: [0, 1],
        duration: 800,
        delay: 600,
        easing: 'easeInOutQuad'
    });

    function animateProcessLine() {
        const processLine = document.querySelector('.process-line');
        const processSteps = document.querySelectorAll('.process-step');
        
        if (!processLine) return;
        
        processLine.style.opacity = '0';
        processLine.style.transform = 'scaleY(0)';
        processLine.style.transformOrigin = 'top center';
        
        anime({
            targets: processLine,
            opacity: [0, 0.3],
            scaleY: [0, 1],
            duration: 1500,
            delay: 800,
            easing: 'easeOutCubic'
        });
        
        let hasAnimated = false;
        
        const lineObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && !hasAnimated) {
                    hasAnimated = true;
                    
                    anime({
                        targets: processLine,
                        background: [
                            'linear-gradient(180deg, #0052cc 0%, transparent 100%)',
                            'linear-gradient(180deg, #0052cc 0%, #0052cc 100%)'
                        ],
                        duration: 2000,
                        easing: 'easeInOutQuad',
                        delay: 300
                    });
                }
            });
        }, {
            threshold: 0.3
        });
        
        lineObserver.observe(processLine);
        
        processSteps.forEach((step, index) => {
            const stepObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        step.classList.add('active');
                        
                        const progress = ((index + 1) / processSteps.length) * 100;
                        
                        anime({
                            targets: processLine,
                            background: `linear-gradient(180deg, #0052cc 0%, #0052cc ${progress}%, rgba(0, 82, 204, 0.3) ${progress}%, rgba(0, 82, 204, 0.3) 100%)`,
                            duration: 1000,
                            easing: 'easeOutCubic'
                        });
                        
                        anime({
                            targets: step.querySelector('.step-circle'),
                            scale: [0.8, 1],
                            opacity: [0, 1],
                            duration: 600,
                            easing: 'easeOutElastic(1, .6)'
                        });
                    } else {
                        step.classList.remove('active');
                    }
                });
            }, {
                threshold: 0.6,
                rootMargin: '-50px 0px -100px 0px'
            });
            
            stepObserver.observe(step);
        });
    }

    setTimeout(animateProcessLine, 1000);

    window.addEventListener('scroll', function() {
        const scrolled = window.pageYOffset;
        const hero = document.querySelector('.services-hero');
        if (hero) {
            hero.style.transform = `translateY(${scrolled * 0.5}px)`;
        }
    });

    document.querySelectorAll('.service-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            anime({
                targets: this,
                scale: [1, 0.95, 1],
                duration: 300,
                easing: 'easeInOutQuad'
            });
        });
    });

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                anime({
                    targets: entry.target.querySelector('.service-icon'),
                    scale: [0, 1],
                    rotate: [180, 0],
                    duration: 800,
                    easing: 'easeOutElastic(1, .8)'
                });
            }
        });
    }, {
        threshold: 0.5,
        rootMargin: '0px 0px -100px 0px'
    });

    document.querySelectorAll('.service-item').forEach(item => {
        observer.observe(item);
    });
});