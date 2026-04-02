document.addEventListener('DOMContentLoaded', function() {
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
                }, 300);
            }
        });
    });
    
    const modal = document.createElement('div');
    modal.className = 'image-modal';
    modal.innerHTML = `
        <span class="close-modal">&times;</span>
        <img class="modal-content" id="modal-image">
    `;
    document.body.appendChild(modal);
    
    const modalImg = document.getElementById('modal-image');
    const closeModal = document.querySelector('.close-modal');
    
    document.querySelectorAll('.zoomable').forEach(img => {
        img.addEventListener('click', function() {
            modal.style.display = 'block';
            modalImg.src = this.src;
            modalImg.alt = this.alt;
        });
    });
    
    closeModal.addEventListener('click', function() {
        modal.style.display = 'none';
    });
    
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.style.display === 'block') {
            modal.style.display = 'none';
        }
    });
    
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.project-stage').forEach((stage, index) => {
        stage.style.opacity = '0';
        stage.style.transform = 'translateY(20px)';
        stage.style.transition = `opacity 0.5s ease ${index * 0.1}s, transform 0.5s ease ${index * 0.1}s`;
        observer.observe(stage);
    });
});