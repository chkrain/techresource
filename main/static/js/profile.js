document.addEventListener('DOMContentLoaded', function() {
    const navItems = document.querySelectorAll('.nav-item');
    const tabContents = document.querySelectorAll('.tab-content');
    
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            
            navItems.forEach(nav => nav.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            this.classList.add('active');
            
            const tabId = this.getAttribute('data-tab');
            const targetTab = document.getElementById(tabId);
            if (targetTab) {
                targetTab.classList.add('active');
            }
        });
    });
    
    const phoneInput = document.querySelector('input[type="tel"]');
    if (phoneInput) {
        phoneInput.addEventListener('input', function(e) {
            let value = this.value.replace(/\D/g, '');
            
            if (value.startsWith('7') || value.startsWith('8')) {
                value = value.substring(1);
            }
            
            let formattedValue = '+7 (';
            
            if (value.length > 0) {
                formattedValue += value.substring(0, 3);
            }
            if (value.length > 3) {
                formattedValue += ') ' + value.substring(3, 6);
            }
            if (value.length > 6) {
                formattedValue += '-' + value.substring(6, 8);
            }
            if (value.length > 8) {
                formattedValue += '-' + value.substring(8, 10);
            }
            
            this.value = formattedValue;
        });
    }
    
    document.querySelectorAll('.form-input, .form-select, .form-textarea').forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            if (!this.value) {
                this.parentElement.classList.remove('focused');
            }
        });
    });
    
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            if (!confirm('Вы уверены, что хотите удалить этот адрес?')) {
                e.preventDefault();
            } else {
                const card = this.closest('.address-card');
                if (card) {
                    card.style.opacity = '0';
                    card.style.transform = 'translateX(-100px)';
                    setTimeout(() => {
                        card.remove();
                    }, 300);
                }
            }
        });
    });
    
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            let isValid = true;
            const requiredFields = this.querySelectorAll('[required]');
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.style.borderColor = '#e53e3e';
                } else {
                    field.style.borderColor = '#48bb78';
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                const errorMsg = document.createElement('div');
                errorMsg.className = 'form-error';
                errorMsg.textContent = 'Пожалуйста, заполните все обязательные поля';
                errorMsg.style.marginTop = '1rem';
                errorMsg.style.padding = '1rem';
                errorMsg.style.background = '#fff5f5';
                errorMsg.style.borderRadius = '8px';
                errorMsg.style.border = '1px solid #fed7d7';
                
                const existingError = this.querySelector('.submit-error');
                if (existingError) {
                    existingError.remove();
                }
                
                errorMsg.className = 'submit-error';
                this.appendChild(errorMsg);
                
                errorMsg.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
    });
});