class DeliveryCalculator {
    constructor() {
        this.addressSelect = document.getElementById('id_address_id');
        this.cartTotal = document.getElementById('cart-total').dataset.total;
        
        if (this.addressSelect) {
            this.init();
        }
    }
    
    init() {
        this.addressSelect.addEventListener('change', this.handleAddressChange.bind(this));
        
        if (this.addressSelect.value) {
            this.calculateDelivery();
        }
    }
    
    handleAddressChange(event) {
        this.calculateDelivery();
    }
    
    calculateDelivery() {
        const addressId = this.addressSelect.value;
        
        if (!addressId) {
            this.updateDeliveryInfo(0, {});
            return;
        }
        
        fetch('/api/calculate-delivery/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({
                address_id: addressId,
                cart_total: this.cartTotal
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.updateDeliveryInfo(data.delivery_cost, data.delivery_info);
            } else {
                console.error('Ошибка расчета доставки:', data.error);
            }
        })
        .catch(error => {
            console.error('Ошибка:', error);
        });
    }
    
    updateDeliveryInfo(cost, info) {
        const deliveryCostElement = document.getElementById('delivery-cost');
        const finalPriceElement = document.getElementById('final-price');
        
        if (deliveryCostElement && finalPriceElement) {
            deliveryCostElement.textContent = cost.toLocaleString('ru-RU') + ' ₽';
            
            const subtotal = parseFloat(document.getElementById('subtotal').dataset.value);
            const paymentFee = parseFloat(document.getElementById('payment-fee').dataset.value);
            const finalPrice = subtotal + cost + paymentFee;
            
            finalPriceElement.textContent = finalPrice.toLocaleString('ru-RU') + ' ₽';
        }
        
        this.updateDeliveryDetails(info);
    }
    
    updateDeliveryDetails(info) {
        const detailsElement = document.getElementById('delivery-details');
        if (!detailsElement) return;
        
        if (Object.keys(info).length === 0) {
            detailsElement.innerHTML = '<p class="text-muted">Выберите адрес для расчета доставки</p>';
            return;
        }
        
        let html = `
            <div class="delivery-info">
                <p><strong>Зона доставки:</strong> ${info.zone}</p>
                <p><strong>Срок доставки:</strong> ${info.time}</p>
                <p><strong>Доступные службы:</strong> ${info.couriers.join(', ')}</p>
        `;
        
        if (info.free_delivery_threshold) {
            const remaining = info.free_delivery_threshold - parseFloat(this.cartTotal);
            if (remaining > 0) {
                html += `<p class="text-success"><small>Добавьте товаров на ${remaining.toLocaleString('ru-RU')} ₽ для бесплатной доставки</small></p>`;
            } else {
                html += `<p class="text-success"><strong>✓ Бесплатная доставка</strong></p>`;
            }
        }
        
        html += `</div>`;
        detailsElement.innerHTML = html;
    }
    
    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    new DeliveryCalculator();
});