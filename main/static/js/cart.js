document.addEventListener('DOMContentLoaded', function() {
    function initCustomSelect() {
        const originalSelect = document.getElementById('address-select');
        const customSelect = document.querySelector('.custom-select');
        const customTrigger = document.querySelector('.custom-select-trigger');
        const customOptions = document.querySelector('.custom-select-options');
        const customSelectWrapper = document.querySelector('.custom-select-wrapper');
        
        if (!originalSelect || !customSelect) return;
        
        function updateCustomSelectDisplay() {
            const selectedOption = originalSelect.options[originalSelect.selectedIndex];
            
            if (selectedOption.value) {
                const textParts = selectedOption.text.split('|');
                customTrigger.innerHTML = `
                    <span class="selected-text">
                        <span class="option-title">${textParts[0] || 'Адрес'}</span>
                        <span class="option-details">${textParts[1] || 'Не указан'}</span>
                    </span>
                    <span class="custom-arrow">▼</span>
                `;
                customTrigger.classList.remove('placeholder');
                customSelectWrapper.classList.remove('error');
                customSelectWrapper.classList.add('success');
                
                if (customOptions) {
                    customOptions.querySelectorAll('.custom-select-option').forEach(opt => {
                        opt.classList.remove('selected');
                        if (opt.getAttribute('data-value') === selectedOption.value) {
                            opt.classList.add('selected');
                        }
                    });
                }
            } else {
                customTrigger.innerHTML = `
                    <span class="selected-text">Выберите адрес доставки</span>
                    <span class="custom-arrow">▼</span>
                `;
                customTrigger.classList.add('placeholder');
                customSelectWrapper.classList.remove('success');
            }
        }
        
        updateCustomSelectDisplay();
        
        if (customTrigger) {
            customTrigger.addEventListener('click', function(e) {
                e.stopPropagation();
                const isOpen = customSelect.classList.contains('open');
                
                document.querySelectorAll('.custom-select.open').forEach(select => {
                    if (select !== customSelect) {
                        select.classList.remove('open');
                    }
                });
                
                customSelect.classList.toggle('open');
                
                if (!isOpen && customOptions) {
                    const selectedOption = customOptions.querySelector('.custom-select-option.selected');
                    if (selectedOption) {
                        selectedOption.scrollIntoView({ block: 'nearest' });
                    }
                }
            });
        }
        
        if (customOptions) {
            customOptions.querySelectorAll('.custom-select-option').forEach(option => {
                option.addEventListener('click', function() {
                    const value = this.getAttribute('data-value');
                    
                    originalSelect.value = value;
                    
                    updateCustomSelectDisplay();
                    
                    customSelect.classList.remove('open');
                });
            });
        }
        
        // Закрытие при клике вне элемента
        document.addEventListener('click', function(e) {
            if (customSelect && !customSelect.contains(e.target)) {
                customSelect.classList.remove('open');
            }
        });
        
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && customSelect && customSelect.classList.contains('open')) {
                customSelect.classList.remove('open');
            }
        });
        
        originalSelect.addEventListener('change', function() {
            updateCustomSelectDisplay();
        });
    }
    
    if (document.getElementById('address-select')) {
        initCustomSelect();
    }
    
    const orderForm = document.querySelector('.order-form');
    if (orderForm) {
        orderForm.addEventListener('submit', function(e) {
            const addressSelect = document.getElementById('address-select');
            const customSelectWrapper = document.querySelector('.custom-select-wrapper');
            
            if (addressSelect && (!addressSelect.value || addressSelect.value === '')) {
                if (customSelectWrapper) {
                    customSelectWrapper.classList.add('error');
                    customSelectWrapper.classList.remove('success');
                    
                    let errorMessage = customSelectWrapper.querySelector('.custom-error-message');
                    if (!errorMessage) {
                        errorMessage = document.createElement('div');
                        errorMessage.className = 'custom-error-message';
                        errorMessage.style.cssText = `
                            color: #e53e3e;
                            font-size: 0.8rem;
                            margin-top: 0.25rem;
                            padding: 0.25rem 0.5rem;
                            background: #fed7d7;
                            border-radius: 4px;
                            border-left: 3px solid #e53e3e;
                        `;
                        customSelectWrapper.appendChild(errorMessage);
                    }
                    errorMessage.textContent = 'Пожалуйста, выберите адрес доставки';
                }
                
                e.preventDefault();
                
                if (customSelectWrapper) {
                    customSelectWrapper.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    
                    const customSelect = document.querySelector('.custom-select');
                    if (customSelect) {
                        customSelect.classList.add('open');
                    }
                }
            } else {
                if (customSelectWrapper) {
                    customSelectWrapper.classList.remove('error');
                    const errorMessage = customSelectWrapper.querySelector('.custom-error-message');
                    if (errorMessage) {
                        errorMessage.remove();
                    }
                }
            }
        });
    }
});