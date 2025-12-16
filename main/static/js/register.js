document.addEventListener('DOMContentLoaded', function() {
    if (typeof AOS !== 'undefined') {
        AOS.init({
            duration: 800,
            once: true,
            offset: 50
        });
    }

    const accountTypeRadios = document.querySelectorAll('input[name="account_type"]');
    const individualFields = document.getElementById('individual-fields');
    const legalFields = document.getElementById('legal-fields');

    function toggleAccountFields() {
        const selectedType = document.querySelector('input[name="account_type"]:checked').value;
        
        console.log('Selected type:', selectedType);
        
        if (selectedType === 'individual') {
            individualFields.style.display = 'block';
            legalFields.style.display = 'none';
            
            document.querySelectorAll('.individual-field').forEach(input => {
                if (input.name === 'first_name' || input.name === 'last_name') {
                    input.required = true;
                }
            });
            document.querySelectorAll('.legal-field').forEach(input => {
                input.required = false;
            });
            
        } else {
            individualFields.style.display = 'none';
            legalFields.style.display = 'block';
            
            document.querySelectorAll('.individual-field').forEach(input => {
                input.required = false;
            });
            document.querySelectorAll('.legal-field').forEach(input => {
                if (input.name === 'company_name' || input.name === 'inn' || input.name === 'legal_address') {
                    input.required = true;
                }
            });
        }
    }

    accountTypeRadios.forEach(radio => {
        radio.addEventListener('change', toggleAccountFields);
    });

    toggleAccountFields();

    const passwordInput = document.querySelector('input[name="password1"]');
    const passwordConfirmInput = document.querySelector('input[name="password2"]');
    const passwordStrength = document.getElementById('password-strength');
    const passwordStrengthFill = document.getElementById('password-strength-fill');
    const passwordMatch = document.getElementById('password-match');

    function validatePassword(password) {
        const errors = [];
        
        if (password.length < 6) {
            errors.push('Пароль должен содержать минимум 6 символов');
        }
        
        if (password.toLowerCase() === '{{ form.email.value|default:""|lower }}') {
            errors.push('Пароль не должен совпадать с email');
        }
        
        return errors;
    }

    function updatePasswordStrength(password) {
        let strength = 'weak';
        
        if (password.length >= 10) {
            strength = 'strong';
        } else if (password.length >= 7) {
            strength = 'medium';
        }
        
        passwordStrength.className = 'password-strength ' + strength;
    }

    function checkPasswordMatch() {
        const password = passwordInput.value;
        const confirmPassword = passwordConfirmInput.value;
        
        if (password && confirmPassword) {
            if (password === confirmPassword) {
                passwordMatch.textContent = 'Пароли совпадают';
                passwordMatch.className = 'password-match match';
            } else {
                passwordMatch.textContent = 'Пароли не совпадают';
                passwordMatch.className = 'password-match mismatch';
            }
        } else {
            passwordMatch.className = 'password-match';
        }
    }

    if (passwordInput) {
        passwordInput.addEventListener('input', function(e) {
            const password = e.target.value;
            updatePasswordStrength(password);
            
            const errors = validatePassword(password);
            const errorDiv = passwordInput.parentNode.querySelector('.password-errors');
            
            if (errors.length > 0) {
                if (!errorDiv) {
                    const newErrorDiv = document.createElement('div');
                    newErrorDiv.className = 'password-errors error-message';
                    passwordInput.parentNode.appendChild(newErrorDiv);
                }
                const errorDiv = passwordInput.parentNode.querySelector('.password-errors');
                errorDiv.innerHTML = errors.map(error => 
                    `<span class="error-icon">⚠</span> ${error}`
                ).join('<br>');
            } else if (errorDiv) {
                errorDiv.remove();
            }
        });
    }

    if (passwordConfirmInput) {
        passwordConfirmInput.addEventListener('input', checkPasswordMatch);
    }

    function initMasks() {
        const innInput = document.querySelector('input[name="inn"]');
        if (innInput) {
            innInput.addEventListener('input', function(e) {
                let value = e.target.value.replace(/\D/g, '');
                if (value.length > 12) value = value.slice(0, 12);
                e.target.value = value;
            });
        }

        const kppInput = document.querySelector('input[name="kpp"]');
        if (kppInput) {
            kppInput.addEventListener('input', function(e) {
                let value = e.target.value.replace(/\D/g, '');
                if (value.length > 9) value = value.slice(0, 9);
                e.target.value = value;
            });
        }

        const ogrnInput = document.querySelector('input[name="ogrn"]');
        if (ogrnInput) {
            ogrnInput.addEventListener('input', function(e) {
                let value = e.target.value.replace(/\D/g, '');
                if (value.length > 13) value = value.slice(0, 13);
                e.target.value = value;
            });
        }

        const bikInput = document.querySelector('input[name="bik"]');
        if (bikInput) {
            bikInput.addEventListener('input', function(e) {
                let value = e.target.value.replace(/\D/g, '');
                if (value.length > 9) value = value.slice(0, 9);
                e.target.value = value;
            });
        }

        const accountInput = document.querySelector('input[name="settlement_account"]');
        if (accountInput) {
            accountInput.addEventListener('input', function(e) {
                let value = e.target.value.replace(/\D/g, '');
                if (value.length > 20) value = value.slice(0, 20);
                e.target.value = value;
            });
        }
    }

    initMasks();

    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            const accountType = document.querySelector('input[name="account_type"]:checked').value;
            let isValid = true;
            const errorMessages = [];

            const requiredFields = registerForm.querySelectorAll('[required]');
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('error');
                    const fieldName = field.getAttribute('name') || field.previousElementSibling?.textContent || 'поле';
                    errorMessages.push(`Заполните обязательное поле: ${fieldName}`);
                } else {
                    field.classList.remove('error');
                }
            });

            const password = passwordInput?.value;
            if (password) {
                const passwordErrors = validatePassword(password);
                if (passwordErrors.length > 0) {
                    isValid = false;
                    errorMessages.push(...passwordErrors);
                }
            }

            if (passwordInput && passwordConfirmInput && passwordInput.value !== passwordConfirmInput.value) {
                isValid = false;
                errorMessages.push('Пароли не совпадают');
            }

            if (accountType === 'legal') {
                const inn = document.querySelector('input[name="inn"]').value;
                if (inn && (inn.length !== 10 && inn.length !== 12)) {
                    isValid = false;
                    errorMessages.push('ИНН должен содержать 10 или 12 цифр');
                }
            }

            if (!isValid) {
                e.preventDefault();
                showNotification(errorMessages.join('<br>'), 'error');
            }
        });
    }

    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-icon">${type === 'error' ? '⚠' : 'ℹ'}</span>
                <span class="notification-message">${message}</span>
            </div>
        `;
        
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'error' ? '#fed7d7' : '#bee3f8'};
            color: ${type === 'error' ? '#742a2a' : '#2a4365'};
            border: 1px solid ${type === 'error' ? '#feb2b2' : '#90cdf4'};
            border-radius: 8px;
            padding: 1rem;
            max-width: 400px;
            z-index: 10000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    function createAuthParticles() {
        const container = document.getElementById('auth-particles');
        if (!container) return;
        
        const particlesCount = 30;
        
        for (let i = 0; i < particlesCount; i++) {
            const particle = document.createElement('div');
            const size = Math.random() * 4 + 2;
            const duration = Math.random() * 10 + 5;
            const delay = Math.random() * 5;
            
            particle.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                background: rgba(255, 255, 255, ${Math.random() * 0.3 + 0.1});
                border-radius: 50%;
                left: ${Math.random() * 100}%;
                top: ${Math.random() * 100}%;
                animation: float ${duration}s ease-in-out ${delay}s infinite;
            `;
            container.appendChild(particle);
        }
    }

    createAuthParticles();
});