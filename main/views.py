# main/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import login
from django.utils import timezone
import json
import requests
from .models import NotificationLog
import uuid
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from .models import Product, Cart, CartItem, Order, OrderItem, UserProfile, Address
from .forms import UserRegisterForm, UserProfileForm, AddressForm

# Импорт ЮКассы
from yookassa import Payment, Configuration
from django.db.models import Sum

# Настройка ЮКассы
Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

def index(request):
    featured_products = Product.objects.filter(is_active=True, quantity__gt=0)[:6]
    return render(request, 'main/index.html', {'featured_products': featured_products})

def about(request):
    return render(request, 'main/about.html')

def services(request):
    return render(request, 'main/services.html')

@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('index')
    
    # Получаем заказы с фильтрами
    orders = Order.objects.all().order_by('-created_at')
    
    # Фильтрация по статусу
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Фильтрация по дате
    date_filter = request.GET.get('date')
    if date_filter:
        orders = orders.filter(created_at__date=date_filter)
    
    # Статистика
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    paid_orders = Order.objects.filter(status='paid').count()
    
    # Выручка (только оплаченные заказы)
    total_revenue = Order.objects.filter(status='paid').aggregate(
        total=Sum('total_price')
    )['total'] or 0
    
    context = {
        'orders': orders,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'paid_orders': paid_orders,
        'total_revenue': total_revenue,
        'status_choices': Order.STATUS_CHOICES,
        'selected_status': status_filter,
        'selected_date': date_filter,
    }
    
    return render(request, 'main/admin_dashboard.html', context)

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
        
        # Очищаем корзину
        cart_items.delete()
        
        if payment_method == 'card':
            return redirect('create_payment', order_id=order.id)
        else:
            # Для оплаты по счету сразу отмечаем как оплачен (т.к. оплата происходит позже)
            order.status = 'processing'
            order.save()
            
            # Отправляем уведомление о новом заказе по счету
            send_invoice_order_notification(order)
            
            messages.success(request, f'Заказ #{order.id} создан! Мы вышлем счет на вашу почту {request.user.email}.')
            return redirect('orders')
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'addresses': addresses,
    }
    return render(request, 'main/cart.html', context)


def send_invoice_order_notification(order):
    """Отправка уведомления о заказе по счету"""
    try:
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            print("⚠️ TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не настроены")
            return False
            
        message = f"""
📄 <b>НОВЫЙ ЗАКАЗ ПО СЧЕТУ #{order.id}</b>

👤 <b>Клиент:</b> {order.customer_name}
📞 <b>Телефон:</b> {order.customer_phone}
📧 <b>Email:</b> {order.customer_email}
💰 <b>Сумма:</b> {order.total_price} руб.
🚚 <b>Адрес:</b> {order.delivery_address}
📦 <b>Статус:</b> {order.get_status_display()}

<b>Товары:</b>
"""
        
        for item in order.orderitem_set.all():
            message += f"• {item.product.name} x{item.quantity} - {item.get_total_price()} руб.\n"
        
        message += f"\n<b>Итого:</b> {order.total_price} руб."
        message += f"\n\n💡 <b>Требуется выставить счет для оплаты</b>"
        
        # Отправка в Telegram
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': settings.TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления о заказе по счету: {e}")
        return False

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
def create_payment(request, order_id):
    """Создание платежа в ЮКассе"""
    order = get_object_or_404(Order, id=order_id, user=request.user, status='pending')
    
    try:
        # Создаем описание товаров для чека
        items = []
        for item in order.orderitem_set.all():
            items.append({
                "description": item.product.name[:128],  # Ограничение длины описания
                "quantity": str(item.quantity),
                "amount": {
                    "value": f"{item.price:.2f}",
                    "currency": "RUB"
                },
                "vat_code": "1",  # НДС 20%
            })
        
        # Создаем платеж
        payment = Payment.create({
            "amount": {
                "value": f"{order.total_price:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": f"{request.scheme}://{request.get_host()}/payment/success/{order.id}/"
            },
            "capture": True,
            "description": f"Заказ #{order.id}",
            "metadata": {
                "order_id": order.id,
                "user_id": request.user.id
            },
            "receipt": {
                "customer": {
                    "email": order.customer_email
                },
                "items": items
            }
        }, str(uuid.uuid4()))
        
        # Сохраняем ID платежа в заказе
        order.payment_id = payment.id
        order.save()
        
        # Перенаправляем на страницу оплаты ЮКассы
        return redirect(payment.confirmation.confirmation_url)
        
    except Exception as e:
        messages.error(request, f'Ошибка при создании платежа: {str(e)}')
        return redirect('orders')

@login_required
def payment_success(request, order_id):
    """Страница статуса оплаты"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Проверяем статус платежа
    try:
        payment = Payment.find_one(order.payment_id)
        
        if payment.status == 'succeeded':
            if order.status != 'paid':
                order.status = 'paid'
                order.paid_at = timezone.now()
                order.save()
                
                # Уменьшаем количество товаров
                for item in order.orderitem_set.all():
                    item.product.quantity -= item.quantity
                    item.product.save()
                
                send_order_notification(order)
                messages.success(request, 'Оплата прошла успешно! Заказ подтвержден.')
        elif payment.status == 'canceled':
            if order.status != 'cancelled':
                order.status = 'cancelled'
                order.save()
                messages.error(request, 'Платеж был отменен.')
        elif payment.status == 'pending':
            messages.info(request, 'Платеж обрабатывается. Мы уведомим вас, когда он будет завершен.')
        else:
            messages.warning(request, f'Статус платежа: {payment.status}')
            
    except Exception as e:
        messages.error(request, f'Ошибка при проверке платежа: {str(e)}')
    
    return render(request, 'main/payment_success.html', {'order': order})

@csrf_exempt
def yookassa_webhook(request):
    """Webhook для уведомлений от ЮКассы"""
    if request.method == 'POST':
        try:
            # Получаем данные от ЮКассы
            event_json = json.loads(request.body.decode('utf-8'))
            
            # Проверяем подпись (рекомендуется для безопасности)
            # Для демо пропускаем, но в продакшене нужно реализовать
            
            # Обрабатываем разные события
            event_type = event_json.get('event')
            
            if event_type == 'payment.succeeded':
                payment_id = event_json['object']['id']
                
                # Ищем заказ по payment_id
                try:
                    order = Order.objects.get(payment_id=payment_id)
                    
                    # Обновляем статус заказа только если еще не оплачен
                    if order.status != 'paid':
                        order.status = 'paid'
                        order.paid_at = timezone.now()
                        order.save()
                        
                        # Уменьшаем количество товаров
                        for item in order.orderitem_set.all():
                            if item.product.quantity >= item.quantity:
                                item.product.quantity -= item.quantity
                                item.product.save()
                            else:
                                # Логируем проблему с количеством
                                print(f"⚠️ Недостаточно товара {item.product.name} для заказа #{order.id}")
                        
                        # Отправляем уведомления
                        send_order_notification(order)
                        
                        # Сохраняем в историю уведомлений
                        NotificationLog.objects.create(
                            order=order,
                            notification_type='payment_success',
                            message=f'Заказ #{order.id} оплачен через webhook',
                            sent_to=order.customer_email
                        )
                        
                        print(f"✅ Заказ #{order.id} оплачен через webhook")
                    
                except Order.DoesNotExist:
                    print(f"❌ Заказ с payment_id {payment_id} не найден")
                    return JsonResponse({'status': 'order not found'}, status=404)
            
            elif event_type == 'payment.canceled':
                payment_id = event_json['object']['id']
                try:
                    order = Order.objects.get(payment_id=payment_id)
                    if order.status != 'cancelled':
                        order.status = 'cancelled'
                        order.save()
                        print(f"❌ Заказ #{order.id} отменен через webhook")
                except Order.DoesNotExist:
                    pass
            
            return JsonResponse({'status': 'ok'})
            
        except Exception as e:
            print(f"❌ Ошибка в webhook: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'method not allowed'}, status=405)

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
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            print("⚠️ TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не настроены")
            
            # Логируем отсутствие настроек
            NotificationLog.objects.create(
                order=order,
                notification_type='telegram_sent',
                message='Настройки Telegram не настроены',
                success=False,
                error_message='TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не настроены'
            )
            return False
            
        message = f"""
🛒 <b>НОВЫЙ ОПЛАЧЕННЫЙ ЗАКАЗ #{order.id}</b>

👤 <b>Клиент:</b> {order.customer_name}
📞 <b>Телефон:</b> {order.customer_phone}
📧 <b>Email:</b> {order.customer_email}
💰 <b>Сумма:</b> {order.total_price} руб.
🚚 <b>Адрес:</b> {order.delivery_address}
💳 <b>Оплата:</b> {order.get_payment_method_display()}
⏰ <b>Время оплаты:</b> {order.paid_at.strftime('%d.%m.%Y %H:%M') if order.paid_at else 'Не указано'}

<b>Товары:</b>
"""
        
        for item in order.orderitem_set.all():
            message += f"• {item.product.name} x{item.quantity} - {item.get_total_price()} руб.\n"
        
        message += f"\n<b>Итого:</b> {order.total_price} руб."
        
        # Отправка в Telegram
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': settings.TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            # Логируем успешную отправку
            NotificationLog.objects.create(
                order=order,
                notification_type='telegram_sent',
                message='Уведомление отправлено в Telegram',
                sent_to=f"Telegram chat: {settings.TELEGRAM_CHAT_ID}",
                success=True
            )
            return True
        else:
            # Логируем ошибку
            NotificationLog.objects.create(
                order=order,
                notification_type='telegram_sent',
                message=f'Ошибка отправки в Telegram: {response.status_code}',
                sent_to=f"Telegram chat: {settings.TELEGRAM_CHAT_ID}",
                success=False,
                error_message=response.text
            )
            return False
        
    except Exception as e:
        error_msg = f"❌ Ошибка отправки в Telegram: {e}"
        print(error_msg)
        
        # Логируем исключение
        NotificationLog.objects.create(
            order=order,
            notification_type='telegram_sent',
            message='Исключение при отправке в Telegram',
            success=False,
            error_message=str(e)
        )
        return False
    

def send_cancellation_notification(order):
    """Отправка уведомления об отмене заказа"""
    try:
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            return False
            
        message = f"""
❌ <b>ЗАКАЗ ОТМЕНЕН #{order.id}</b>

👤 <b>Клиент:</b> {order.customer_name}
📞 <b>Телефон:</b> {order.customer_phone}
💰 <b>Сумма:</b> {order.total_price} руб.
🕒 <b>Время отмены:</b> {timezone.now().strftime('%d.%m.%Y %H:%M')}
"""
        
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': settings.TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
        
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