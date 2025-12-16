document.addEventListener('DOMContentLoaded', function() {
    const forgotPasswordLink = document.querySelector('.forgot-password');
    const modal = document.getElementById('forgot-password');
    const modalClose = document.querySelector('.modal-close');
    const closeModalBtn = document.querySelector('.close-modal');

    let currentEmail = '';
    let timerInterval = null;

    if (forgotPasswordLink && modal) {
        forgotPasswordLink.addEventListener('click', function(e) {
            e.preventDefault();
            modal.style.display = 'block';
            resetRecoveryForm();
        });
    }

    function closeModal() {
        modal.style.display = 'none';
        resetRecoveryForm();
    }

    if (modalClose) {
        modalClose.addEventListener('click', closeModal);
    }

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeModal);
    }

    window.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });

    function resetRecoveryForm() {
        goToStep(1);
        clearInterval(timerInterval);
        if (document.getElementById('emailForm')) {
            document.getElementById('emailForm').reset();
        }
        if (document.getElementById('codeForm')) {
            document.getElementById('codeForm').reset();
        }
        if (document.getElementById('passwordForm')) {
            document.getElementById('passwordForm').reset();
        }
        resetPasswordRequirements();
    }

    function goToStep(stepNumber) {
        document.querySelectorAll('.recovery-step').forEach(step => {
            step.classList.remove('active');
        });
        
        const targetStep = document.getElementById(`step${stepNumber}`);
        if (targetStep) {
            targetStep.classList.add('active');
        }
        
        updateProgressBar(stepNumber);
    }

    function updateProgressBar(currentStep) {
        const steps = document.querySelectorAll('.step-circle');
        const lines = document.querySelectorAll('.step-line');
        
        steps.forEach((step, index) => {
            const stepNum = parseInt(step.dataset.step);
            
            step.classList.remove('active', 'completed');
            if (stepNum < currentStep) {
                step.classList.add('completed');
            } else if (stepNum === currentStep) {
                step.classList.add('active');
            }
        });
        
        lines.forEach((line, index) => {
            line.classList.remove('active');
            if (index < currentStep - 1) {
                line.classList.add('active');
            }
        });
    }

    function startTimer() {
        const timerElement = document.getElementById('timer-count');
        const timerContainer = document.getElementById('code-timer');
        
        if (!timerElement || !timerContainer) return;
        
        let timeLeft = 60;
        
        timerContainer.classList.add('active');
        timerContainer.classList.remove('expired');
        
        clearInterval(timerInterval);
        
        timerInterval = setInterval(() => {
            timeLeft--;
            timerElement.textContent = timeLeft;
            
            if (timeLeft <= 0) {
                clearInterval(timerInterval);
                timerContainer.classList.remove('active');
                timerContainer.classList.add('expired');
                timerContainer.innerHTML = 'Не получили код? <a href="#" id="resend-code">Отправить еще раз</a>';
                
                const resendLink = document.getElementById('resend-code');
                if (resendLink) {
                    resendLink.addEventListener('click', function(e) {
                        e.preventDefault();
                        resendCode();
                    });
                }
            }
        }, 1000);
    }

    function resendCode() {
        const formData = new FormData();
        formData.append('email', currentEmail);
        formData.append('csrfmiddlewaretoken', getCSRFToken());
        
        fetch('/password-reset/', {
            method: 'POST',
            body: formData
        }).then(response => response.json())
        .then(data => {
            if (data.success) {
                showRecoverySuccess('Код отправлен повторно');
                startTimer();
            } else {
                showRecoveryError(data.error || 'Ошибка отправки');
            }
        }).catch(error => {
            showRecoveryError('Ошибка сети');
        });
    }

    function validatePassword(password) {
        const requirements = {
            length: password.length >= 8,
            uppercase: /[A-Z]/.test(password),
            lowercase: /[a-z]/.test(password),
            number: /\d/.test(password)
        };
        
        Object.keys(requirements).forEach(req => {
            const element = document.querySelector(`[data-requirement="${req}"]`);
            if (element) {
                element.classList.remove('valid', 'invalid');
                element.classList.add(requirements[req] ? 'valid' : 'invalid');
            }
        });
        
        return Object.values(requirements).every(Boolean);
    }

    function resetPasswordRequirements() {
        document.querySelectorAll('.requirement').forEach(req => {
            req.classList.remove('valid', 'invalid');
        });
    }

    function getCSRFToken() {
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfInput) {
            return csrfInput.value;
        }
        
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            return metaToken.getAttribute('content');
        }
        
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    const emailForm = document.getElementById('emailForm');
    if (emailForm) {
        emailForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const email = formData.get('email');
            currentEmail = email;
            
            if (!isValidEmail(email)) {
                showRecoveryError('Пожалуйста, введите корректный email адрес');
                return;
            }
            
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = 'Отправка...';
            submitBtn.disabled = true;
            
            try {
                const response = await fetch('/password-reset/', {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': getCSRFToken(),
                    },
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    if (document.getElementById('email-display')) {
                        document.getElementById('email-display').textContent = email;
                    }
                    if (document.getElementById('hidden-email')) {
                        document.getElementById('hidden-email').value = email;
                    }
                    goToStep(2);
                    startTimer();
                } else {
                    showRecoveryError(data.error || 'Произошла ошибка');
                }
                
            } catch (error) {
                showRecoveryError('Ошибка сети. Проверьте подключение к интернету.');
            } finally {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        });
    }

    const codeForm = document.getElementById('codeForm');
    if (codeForm) {
        codeForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = 'Проверка...';
            submitBtn.disabled = true;
            
            try {
                const response = await fetch('/password-reset/verify/', {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': getCSRFToken(),
                    },
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    if (document.getElementById('reset-token')) {
                        document.getElementById('reset-token').value = data.reset_token;
                    }
                    goToStep(3);
                    clearInterval(timerInterval);
                } else {
                    showRecoveryError(data.error || 'Неверный код');
                }
                
            } catch (error) {
                showRecoveryError('Ошибка сети');
            } finally {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        });
    }

    const passwordForm = document.getElementById('passwordForm');
    if (passwordForm) {
        const passwordInput = passwordForm.querySelector('input[name="new_password"]');
        if (passwordInput) {
            passwordInput.addEventListener('input', function() {
                validatePassword(this.value);
            });
        }
        
        passwordForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const newPassword = formData.get('new_password');
            const confirmPassword = formData.get('confirm_password');
            
            if (!validatePassword(newPassword)) {
                showRecoveryError('Пароль не соответствует требованиям');
                return;
            }
            
            if (newPassword !== confirmPassword) {
                showRecoveryError('Пароли не совпадают');
                return;
            }
            
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = 'Сохранение...';
            submitBtn.disabled = true;
            
            try {
                const response = await fetch('/password-reset/set-password/', {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': getCSRFToken(),
                    },
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    goToStep(4);
                } else {
                    showRecoveryError(data.error || 'Ошибка сохранения пароля');
                }
                
            } catch (error) {
                showRecoveryError('Ошибка сети');
            } finally {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        });
    }

    function showRecoveryError(message) {
        const existingError = document.querySelector('.recovery-error');
        if (existingError) {
            existingError.remove();
        }
        
        const activeStep = document.querySelector('.recovery-step.active');
        if (!activeStep) return;
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message recovery-error';
        errorDiv.innerHTML = `
            <div class="error-icon">⚠️</div>
            <div class="error-content">
                <strong>Ошибка</strong>
                <p>${message}</p>
            </div>
        `;
        
        activeStep.insertBefore(errorDiv, activeStep.firstChild);
        
        errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function showRecoverySuccess(message) {
        console.log('✅ ' + message);
    }

    document.querySelectorAll('.form-input').forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            if (!this.value) {
                this.parentElement.classList.remove('focused');
            }
        });
    });
    
    const loginForm = document.querySelector('.login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            const username = this.querySelector('input[name="username"]');
            const password = this.querySelector('input[name="password"]');
            let isValid = true;
            
            if (!username || !username.value.trim()) {
                if (username) username.style.borderColor = '#e53e3e';
                isValid = false;
            } else {
                username.style.borderColor = '#48bb78';
            }
            
            if (!password || !password.value.trim()) {
                if (password) password.style.borderColor = '#e53e3e';
                isValid = false;
            } else {
                password.style.borderColor = '#48bb78';
            }
            
            if (!isValid) {
                e.preventDefault();
                
                let errorMsg = this.querySelector('.validation-error');
                if (!errorMsg) {
                    errorMsg = document.createElement('div');
                    errorMsg.className = 'error-message validation-error';
                    errorMsg.innerHTML = `
                        <div class="error-icon">⚠️</div>
                        <div class="error-content">
                            <strong>Заполните все поля</strong>
                            <p>Пожалуйста, введите имя пользователя и пароль</p>
                        </div>
                    `;
                    this.insertBefore(errorMsg, this.firstChild);
                }
                
                errorMsg.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
    }
    
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
    
    document.querySelectorAll('.login-card, .benefits-card').forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(card);
    });
});