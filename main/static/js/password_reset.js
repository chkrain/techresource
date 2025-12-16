document.addEventListener('DOMContentLoaded', function() {
    const card = document.querySelector('.password-reset-card');
    if (card) {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 100);
    }
    
    const inputs = document.querySelectorAll('.form-input');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            if (!this.value) {
                this.parentElement.classList.remove('focused');
            }
        });
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const successIcon = document.querySelector('.success-icon');
    if (successIcon) {
        setTimeout(() => {
            successIcon.style.transform = 'scale(1.1)';
            setTimeout(() => {
                successIcon.style.transform = 'scale(1)';
            }, 300);
        }, 1000);
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const passwordInput = document.querySelector('input[name="new_password1"]');
    const confirmPasswordInput = document.querySelector('input[name="new_password2"]');
    
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            validatePassword(this.value);
            validatePasswordMatch();
        });
        
        passwordInput.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        passwordInput.addEventListener('blur', function() {
            if (!this.value) {
                this.parentElement.classList.remove('focused');
            }
        });
    }
    
    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', function() {
            validatePasswordMatch();
        });
        
        confirmPasswordInput.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        confirmPasswordInput.addEventListener('blur', function() {
            if (!this.value) {
                this.parentElement.classList.remove('focused');
            }
        });
    }
    
    function validatePassword(password) {
        const requirements = {
            length: password.length >= 8,
            numeric: !/^\d+$/.test(password), 
            common: !isCommonPassword(password), 
            similarity: !isTooSimilar(password) 
        };
        
        Object.keys(requirements).forEach(req => {
            const element = document.querySelector(`[data-requirement="${req}"]`);
            if (element) {
                element.classList.remove('valid', 'invalid');
                
                if (password.length === 0) {
                    element.classList.remove('valid', 'invalid');
                } else {
                    element.classList.add(requirements[req] ? 'valid' : 'invalid');
                }
            }
        });
        
        return Object.values(requirements).every(Boolean);
    }
    
    function validatePasswordMatch() {
        const password = passwordInput ? passwordInput.value : '';
        const confirmPassword = confirmPasswordInput ? confirmPasswordInput.value : '';
        
        if (confirmPassword && password !== confirmPassword) {
            confirmPasswordInput.style.borderColor = '#ef4444';
            confirmPasswordInput.style.boxShadow = '0 0 0 3px rgba(239, 68, 68, 0.1)';
        } else if (confirmPassword) {
            confirmPasswordInput.style.borderColor = '#10b981';
            confirmPasswordInput.style.boxShadow = '0 0 0 3px rgba(16, 185, 129, 0.1)';
        } else {
            confirmPasswordInput.style.borderColor = '#e9ecef';
            confirmPasswordInput.style.boxShadow = '0 2px 10px rgba(0,0,0,0.04)';
        }
    }
    
    function isCommonPassword(password) {
        const commonPasswords = [
            'password', '123456', '12345678', '1234', 'qwerty', 
            'admin', 'letmein', 'welcome', 'monkey', 'sunshine',
            'password1', '1234567', '123456789', 'abc123', '111111'
        ];
        return commonPasswords.includes(password.toLowerCase());
    }
    
    function isTooSimilar(password) {
        const userInfo = ['admin', 'user', 'test', 'name', 'email'];
        return userInfo.some(info => 
            password.toLowerCase().includes(info.toLowerCase()) && 
            password.length < 12
        );
    }
    
    const form = document.querySelector('.password-reset-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const password = passwordInput ? passwordInput.value : '';
            const confirmPassword = confirmPasswordInput ? confirmPasswordInput.value : '';
            
            if (!validatePassword(password)) {
                e.preventDefault();
                showFormError('Пароль не соответствует требованиям безопасности');
                return;
            }
            
            if (password !== confirmPassword) {
                e.preventDefault();
                showFormError('Пароли не совпадают');
                return;
            }
        });
    }
    
    function showFormError(message) {
        const existingError = document.querySelector('.form-error-message');
        if (existingError) {
            existingError.remove();
        }
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message form-error-message';
        errorDiv.innerHTML = `
            <div class="error-icon">⚠️</div>
            <div class="error-content">
                <strong>Ошибка валидации</strong>
                <p>${message}</p>
            </div>
        `;
        
        form.insertBefore(errorDiv, form.firstChild);
        
        errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const successIcon = document.querySelector('.success-icon');
    if (successIcon) {
        let animationCount = 0;
        const animateIcon = () => {
            if (animationCount < 3) {
                successIcon.style.transform = 'scale(1.1)';
                setTimeout(() => {
                    successIcon.style.transform = 'scale(1)';
                    animationCount++;
                    if (animationCount < 3) {
                        setTimeout(animateIcon, 300);
                    }
                }, 150);
            }
        };
        
        setTimeout(animateIcon, 500);
    }
    
    const createConfetti = () => {
        const colors = ['#667eea', '#764ba2', '#48bb78', '#ed8936', '#f56565'];
        for (let i = 0; i < 30; i++) {
            const confetti = document.createElement('div');
            confetti.style.cssText = `
                position: fixed;
                width: 8px;
                height: 8px;
                background: ${colors[Math.floor(Math.random() * colors.length)]};
                border-radius: 1px;
                top: -10px;
                left: ${Math.random() * 100}%;
                animation: confettiFall ${1 + Math.random() * 2}s linear forwards;
                z-index: 1000;
                pointer-events: none;
            `;
            document.body.appendChild(confetti);
            
            setTimeout(() => confetti.remove(), 2000);
        }
    };
    
    const style = document.createElement('style');
    style.textContent = `
        @keyframes confettiFall {
            0% {
                transform: translateY(0) rotate(0deg);
                opacity: 1;
            }
            100% {
                transform: translateY(100vh) rotate(360deg);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
    
    setTimeout(createConfetti, 800);
});