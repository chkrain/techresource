# main/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import login
from django.utils import timezone
import json
import requests
from django.conf import settings
from .models import Product, Cart, CartItem, Order, OrderItem, UserProfile, Address
from .forms import UserRegisterForm, UserProfileForm, AddressForm

def index(request):
    featured_products = Product.objects.filter(is_active=True, quantity__gt=0)[:6]
    return render(request, 'main/index.html', {'featured_products': featured_products})

def about(request):
    return render(request, 'main/about.html')

def services(request):
    return render(request, 'main/services.html')

def products(request):
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    
    products_list = Product.objects.filter(is_active=True)
    
    if search_query:
        products_list = products_list.filter(name__icontains=search_query)
    
    if category_filter:
        products_list = products_list.filter(category=category_filter)
    
    categories = Product.objects.filter(is_active=True).values_list('category', flat=True).distinct()
    
    context = {
        'products': products_list,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_filter,
    }
    return render(request, 'main/products.html', context)

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('profile')
    else:
        form = UserRegisterForm()
    return render(request, 'main/register.html', {'form': form})

@login_required
def profile(request):
    # Создаем профиль, если его нет
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    addresses = Address.objects.filter(user=request.user)
    
    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, instance=profile)
        address_form = AddressForm(request.POST)
        
        if 'update_profile' in request.POST and profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Профиль обновлен')
            return redirect('profile')
        
        elif 'add_address' in request.POST and address_form.is_valid():
            address = address_form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, 'Адрес добавлен')
            return redirect('profile')
    
    else:
        profile_form = UserProfileForm(instance=profile)
        address_form = AddressForm()
    
    context = {
        'profile_form': profile_form,
        'address_form': address_form,
        'addresses': addresses,
    }
    return render(request, 'main/profile.html', context)

@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.delete()
    messages.success(request, 'Адрес удален')
    return redirect('profile')

@login_required
def add_to_cart(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        # Проверяем наличие товара
        if product.quantity <= 0:
            messages.error(request, 'Товар отсутствует на складе')
            return redirect('products')
        
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': 1}
        )
        
        if not created:
            if cart_item.quantity < product.quantity:
                cart_item.quantity += 1
                cart_item.save()
                messages.success(request, f'Товар "{product.name}" добавлен в корзину')
            else:
                messages.error(request, 'Недостаточно товара в наличии')
        else:
            messages.success(request, f'Товар "{product.name}" добавлен в корзину')
        
        return redirect('products')

@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.cartitem_set.all()
    addresses = Address.objects.filter(user=request.user)
    
    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        payment_method = request.POST.get('payment_method')
        
        if not address_id or not payment_method:
            messages.error(request, 'Выберите адрес доставки и способ оплаты')
            return redirect('cart')
        
        address = get_object_or_404(Address, id=address_id, user=request.user)
        
        # Проверяем наличие товаров
        for cart_item in cart_items:
            if cart_item.quantity > cart_item.product.quantity:
                messages.error(request, f'Недостаточно товара "{cart_item.product.name}" в наличии. Доступно: {cart_item.product.quantity} шт.')
                return redirect('cart')
        
        # Создаем заказ
        order = Order.objects.create(
            user=request.user,
            total_price=cart.get_total_price(),
            payment_method=payment_method,
            customer_name=address.full_name,
            customer_phone=address.phone,
            customer_email=request.user.email,
            delivery_address=f"{address.city}, {address.address}, {address.postal_code}"
        )
        
        # Переносим товары из корзины в заказ
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
        
        # Уменьшаем количество товаров на складе
        for cart_item in cart_items:
            cart_item.product.quantity -= cart_item.quantity
            cart_item.product.save()
        
        # Очищаем корзину
        cart_items.delete()
        
        if payment_method == 'card':
            return redirect('payment', order_id=order.id)
        else:
            messages.success(request, f'Заказ #{order.id} создан! Мы вышлем счет на вашу почту.')
            send_order_notification(order)
            return redirect('orders')
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'addresses': addresses,
    }
    return render(request, 'main/cart.html', context)

@login_required
def update_cart_item(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        action = request.POST.get('action')
        
        if action == 'increase':
            if cart_item.quantity < cart_item.product.quantity:
                cart_item.quantity += 1
                cart_item.save()
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
        elif action == 'remove':
            cart_item.delete()
        
        return redirect('cart')

@login_required
def payment_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user, status='pending')
    
    if request.method == 'POST':
        # Имитация успешной оплаты
        order.status = 'paid'
        order.paid_at = timezone.now()
        order.payment_id = f"pay_{order.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        order.save()
        
        # Уменьшаем количество товаров
        for item in order.orderitem_set.all():
            item.product.quantity -= item.quantity
            item.product.save()
        
        # Отправляем уведомления
        send_order_notification(order)
        send_order_confirmation(order)
        
        messages.success(request, f'Оплата прошла успешно! Заказ #{order.id} оплачен.')
        return redirect('orders')
    
    context = {
        'order': order,
    }
    return render(request, 'main/payment.html', context)

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.can_be_cancelled():
        order.status = 'cancelled'
        order.cancelled_at = timezone.now()
        order.save()
        
        # Возвращаем товары на склад
        for item in order.orderitem_set.all():
            item.product.quantity += item.quantity
            item.product.save()
        
        # Отправляем уведомление об отмене
        send_cancellation_notification(order)
        
        messages.success(request, f'Заказ #{order.id} отменен. Средства будут возвращены.')
    else:
        messages.error(request, 'Невозможно отменить заказ. Срок отмены истек.')
    
    return redirect('orders')

@login_required
def orders_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'main/orders.html', {'orders': orders})

# Функции для уведомлений
def send_order_notification(order):
    """Отправка уведомления в Telegram о новом заказе"""
    try:
        # Формируем сообщение
        message = f"""
🛒 <b>НОВЫЙ ЗАКАЗ #{order.id}</b>

👤 <b>Клиент:</b> {order.customer_name}
📞 <b>Телефон:</b> {order.customer_phone}
📧 <b>Email:</b> {order.customer_email}
💰 <b>Сумма:</b> {order.total_price} руб.
🚚 <b>Адрес:</b> {order.delivery_address}
📦 <b>Статус:</b> {order.get_status_display()}
💳 <b>Оплата:</b> {order.get_payment_method_display()}

<b>Товары:</b>
"""
        
        # Добавляем товары
        for item in order.orderitem_set.all():
            message += f"• {item.product.name} x{item.quantity} - {item.get_total_price()} руб.\n"
        
        message += f"\n<b>Итого:</b> {order.total_price} руб."
        
        # Отправка в Telegram
        if hasattr(settings, 'TELEGRAM_BOT_TOKEN') and hasattr(settings, 'TELEGRAM_CHAT_ID'):
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': settings.TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Уведомление о заказе #{order.id} отправлено в Telegram")
                return True
            else:
                print(f"❌ Ошибка Telegram API: {response.status_code} - {response.text}")
                return False
        else:
            print("⚠️ TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не настроены в settings.py")
            print("Сообщение для администратора:")
            print(message)
            return False
        
    except requests.exceptions.Timeout:
        print("❌ Таймаут при отправке в Telegram")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка подключения к Telegram: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def send_order_confirmation(order):
    """Отправка подтверждения заказа (пока только логируем)"""
    try:
        message = f"""
Подтверждение заказа #{order.id} для {order.customer_email}

Клиент: {order.customer_name}
Телефон: {order.customer_phone}
Сумма: {order.total_price} руб.
Статус: {order.get_status_display()}
Товары:
""" + "\n".join([f"- {item.product.name} x{item.quantity}" 
                for item in order.orderitem_set.all()])

        print("=== ПОДТВЕРЖДЕНИЕ ЗАКАЗА ===")
        print(message)
        print("=============================")
        
        # Пока просто логируем
        
    except Exception as e:
        print(f"Ошибка формирования подтверждения: {e}")

def send_cancellation_notification(order):
    """Отправка уведомления об отмене заказа"""
    try:
        message = f"""
❌ <b>ЗАКАЗ ОТМЕНЕН #{order.id}</b>

👤 <b>Клиент:</b> {order.customer_name}
📞 <b>Телефон:</b> {order.customer_phone}
💰 <b>Сумма:</b> {order.total_price} руб.
🕒 <b>Время отмены:</b> {timezone.now().strftime('%d.%m.%Y %H:%M')}

<b>Товары возвращены на склад:</b>
"""
        
        for item in order.orderitem_set.all():
            message += f"• {item.product.name} x{item.quantity}\n"
        
        # Отправка в Telegram
        if hasattr(settings, 'TELEGRAM_BOT_TOKEN') and hasattr(settings, 'TELEGRAM_CHAT_ID'):
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': settings.TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Уведомление об отмене заказа #{order.id} отправлено в Telegram")
                return True
            else:
                print(f"❌ Ошибка отправки отмены в Telegram: {response.status_code}")
                return False
        
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления об отмене: {e}")
        return False

# API для обновления количества через AJAX
def update_quantity_ajax(request, product_id):
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            data = json.loads(request.body)
            new_quantity = data.get('quantity')
            
            product = get_object_or_404(Product, id=product_id)
            product.quantity = new_quantity
            product.save()
            
            return JsonResponse({'success': True, 'new_quantity': product.quantity})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})