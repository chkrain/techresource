# main/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.utils.html import strip_tags
import json
import hashlib
from django.utils import timezone
import secrets
import requests
from .models import NotificationLog
import uuid
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import random
from datetime import timedelta
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from .forms import SecureUserCreationForm, SecureAuthenticationForm, SecurePasswordResetForm, SecureSetPasswordForm

from .models import Product, Cart, CartItem, Order, OrderItem, UserProfile, Address, NotificationLog, SecurityLog, PasswordResetToken, LoginAttempt
from .forms import SecureUserCreationForm, SecureAuthenticationForm, SecurePasswordResetForm, SecureSetPasswordForm, UserRegisterForm, UserProfileForm, AddressForm


# Импорт ЮКассы
from yookassa import Payment, Configuration
from django.db.models import Sum

User = get_user_model()

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

def privacy_policy(request):
    return render(request, 'main/privacy.html')

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
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)
    
    addresses = Address.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, instance=user_profile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Профиль обновлен')
                return redirect('profile')
            else:
                address_form = AddressForm()
                
        elif 'add_address' in request.POST:
            address_form = AddressForm(request.POST)
            if address_form.is_valid():
                address = address_form.save(commit=False)
                address.user = request.user
                address.save()
                messages.success(request, 'Адрес добавлен')
                return redirect('profile')
            else:
                profile_form = UserProfileForm(instance=user_profile)
    
    else:
        profile_form = UserProfileForm(instance=user_profile)
        address_form = AddressForm()
    
    context = {
        'user_profile': user_profile,  
        'profile_form': profile_form,
        'address_form': address_form,
        'addresses': addresses,
        'orders': orders, 
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
    print(f"DEBUG: add_to_cart called for product {product_id}")
    print(f"DEBUG: Method: {request.method}")
    print(f"DEBUG: AJAX header: {request.headers.get('X-Requested-With')}")
    print(f"DEBUG: User: {request.user}")
    
    if request.method == 'POST':
        try:
            product = Product.objects.get(id=product_id)
            cart, created = Cart.objects.get_or_create(user=request.user)
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            
            if not created:
                cart_item.quantity += 1
                cart_item.save()
            
            cart_count = cart.cartitem_set.count()
            
            print(f"DEBUG: Success - cart_count: {cart_count}")
            
            return JsonResponse({
                'success': True,
                'cart_count': cart_count,
                'message': 'Товар добавлен в корзину'
            })
        except Product.DoesNotExist:
            print("DEBUG: Product not found")
            return JsonResponse({
                'success': False,
                'error': 'Товар не найден'
            })
        except Exception as e:
            print(f"DEBUG: Exception: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    print("DEBUG: Not a POST request or not AJAX")
    # Если это не AJAX запрос, возвращаем JSON с ошибкой
    return JsonResponse({'success': False, 'error': 'Неверный запрос'})

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
        
        # Проверяем AJAX запрос
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if action == 'increase':
            if cart_item.quantity < cart_item.product.quantity:
                cart_item.quantity += 1
                cart_item.save()
                success = True
                message = 'Количество увеличено'
            else:
                success = False
                message = f'Максимальное количество: {cart_item.product.quantity}'
                
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
                success = True
                message = 'Количество уменьшено'
            else:
                cart_item.delete()
                success = True
                message = 'Товар удален из корзины'
                
        elif action == 'remove':
            cart_item.delete()
            success = True
            message = 'Товар удален из корзины'
            
        elif action == 'set':
            # Новое действие - установка конкретного количества
            try:
                new_quantity = int(request.POST.get('quantity', 1))
                if 1 <= new_quantity <= cart_item.product.quantity:
                    cart_item.quantity = new_quantity
                    cart_item.save()
                    success = True
                    message = 'Количество обновлено'
                else:
                    success = False
                    message = f'Количество должно быть от 1 до {cart_item.product.quantity}'
            except ValueError:
                success = False
                message = 'Некорректное количество'
        else:
            success = False
            message = 'Неизвестное действие'

        # Получаем обновленные данные корзины
        cart = Cart.objects.get(user=request.user)
        cart_total = cart.get_total_price()
        item_count = cart.get_items_count()  # Общее количество товаров
        total_quantity = cart.get_total_quantity()  # Количество позиций
        
        if is_ajax:
            response_data = {
                'success': success,
                'message': message,
                'cart_total': float(cart_total),
                'item_count': item_count,
                'total_quantity': total_quantity,
            }
            
            # Добавляем данные об элементе, если он не удален
            if success and action != 'remove' and hasattr(cart_item, 'quantity'):
                response_data.update({
                    'new_quantity': cart_item.quantity,
                    'item_total': float(cart_item.get_total_price())
                })
            
            return JsonResponse(response_data)
        
        # Если не AJAX, показываем сообщения и редирект
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        
        return redirect('cart')
    
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
    
def password_reset_request(request):
    """Восстановление пароля через Email"""
    if request.method == "POST":
        email = request.POST.get('email')
        
        if not email:
            return JsonResponse({
                'success': False,
                'error': 'Пожалуйста, введите email адрес'
            })
        
        # Проверяем валидность email
        if not isValidEmail(email):
            return JsonResponse({
                'success': False,
                'error': 'Пожалуйста, введите корректный email адрес'
            })
        
        # Ищем пользователя по email
        try:
            user = User.objects.get(email=email)
            
            # Генерируем код
            reset_code = str(random.randint(100000, 999999))
            
            # Сохраняем код в профиль
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.sms_code = reset_code
            profile.sms_code_expires = timezone.now() + timedelta(minutes=10)
            profile.save()
            
            # Отправляем email с кодом
            email_sent = send_password_reset_email(email, reset_code)
            
            if email_sent:
                # Логируем отправку
                NotificationLog.objects.create(
                    notification_type='email_sent',
                    message=f'Код восстановления отправлен на {email}',
                    sent_to=email,
                    success=True
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Код восстановления отправлен на ваш email',
                    'email': email,
                    'next_step': 'verify_code'
                })
            else:
                # Логируем ошибку
                NotificationLog.objects.create(
                    notification_type='email_sent',
                    message=f'Ошибка отправки кода на {email}',
                    sent_to=email,
                    success=False,
                    error_message='Ошибка SMTP сервера'
                )
                
                return JsonResponse({
                    'success': False,
                    'error': 'Ошибка отправки email. Попробуйте позже.'
                })
                
        except User.DoesNotExist:
            # Для безопасности не сообщаем, что email не найден
            return JsonResponse({
                'success': True,
                'message': 'Если email зарегистрирован, код будет отправлен'
            })
        except Exception as e:
            print(f"❌ Ошибка при восстановлении пароля: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Произошла ошибка. Попробуйте позже.'
            })
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

def password_reset_confirm(request, uidb64=None, token=None):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Пароль успешно изменен! Теперь вы можете войти с новым паролем.')
                return redirect('login')
        else:
            form = SetPasswordForm(user)
        
        return render(request, 'main/password_reset_confirm.html', {'form': form})
    else:
        messages.error(request, 'Ссылка для восстановления пароля недействительна или устарела.')
        return redirect('password_reset_request')

def password_reset_done(request):
    return render(request, 'main/password_reset_done.html')

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

def set_new_password(request):
    """Установка нового пароля после проверки кода"""
    if request.method == "POST":
        reset_token = request.POST.get('reset_token')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not reset_token or not new_password:
            return JsonResponse({
                'success': False,
                'error': 'Все поля обязательны'
            })
        
        if new_password != confirm_password:
            return JsonResponse({
                'success': False,
                'error': 'Пароли не совпадают'
            })
        
        try:
            profile = UserProfile.objects.get(
                reset_token=reset_token,
                reset_token_expires__gt=timezone.now()
            )
            
            # Устанавливаем новый пароль
            user = profile.user
            user.set_password(new_password)
            user.save()
            
            # Очищаем токен
            profile.reset_token = None
            profile.reset_token_expires = None
            profile.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Пароль успешно изменен!'
            })
            
        except UserProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Ссылка недействительна или устарела'
            })
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

def send_password_reset_email(email, code):
    """Отправка email с кодом восстановления"""
    try:
        subject = "Код восстановления пароля - Техресурс"
        
        message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .code {{ font-size: 32px; font-weight: bold; color: #667eea; text-align: center; margin: 20px 0; padding: 15px; background: white; border-radius: 8px; }}
                .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Техресурс</h1>
                    <p>Восстановление пароля</p>
                </div>
                <div class="content">
                    <h2>Здравствуйте!</h2>
                    <p>Вы запросили восстановление пароля для вашего аккаунта.</p>
                    <p>Используйте следующий код для подтверждения:</p>
                    <div class="code">{code}</div>
                    <p><strong>Код действителен в течение 10 минут.</strong></p>
                    <p>Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.</p>
                </div>
                <div class="footer">
                    <p>С уважением,<br>Команда Техресурс</p>
                    <p>Это письмо отправлено автоматически, пожалуйста, не отвечайте на него.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        plain_message = f"""
        Восстановление пароля - Техресурс
        
        Здравствуйте!
        
        Вы запросили восстановление пароля для вашего аккаунта.
        Используйте следующий код для подтверждения:
        
        {code}
        
        Код действителен в течение 10 минут.
        
        Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.
        
        С уважением,
        Команда Техресурс
        """
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
            html_message=message
        )
        return True
        
    except Exception as e:
        print(f"❌ Ошибка отправки email: {e}")
        return False
    
def verify_reset_code(request):
    """Проверка кода восстановления"""
    if request.method == "POST":
        email = request.POST.get('email')
        code = request.POST.get('code')
        
        if not email or not code:
            return JsonResponse({
                'success': False,
                'error': 'Все поля обязательны для заполнения'
            })
        
        try:
            user = User.objects.get(email=email)
            profile = UserProfile.objects.get(user=user)
            
            # Проверяем код и его срок действия
            if (profile.sms_code == code and 
                profile.sms_code_expires and 
                profile.sms_code_expires > timezone.now()):
                
                # Код верный, генерируем временный токен
                reset_token = str(uuid.uuid4())
                profile.sms_code = None
                profile.sms_code_expires = None
                profile.reset_token = reset_token
                profile.reset_token_expires = timezone.now() + timedelta(hours=1)
                profile.save()
                
                # Логируем успешную проверку
                NotificationLog.objects.create(
                    notification_type='email_sent',
                    message=f'Код подтвержден для {email}',
                    sent_to=email,
                    success=True
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Код подтвержден',
                    'reset_token': reset_token,
                    'next_step': 'set_password'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Неверный код или код устарел'
                })
                
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Пользователь не найден'
            })
        except Exception as e:
            print(f"❌ Ошибка при проверке кода: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Произошла ошибка. Попробуйте позже.'
            })
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

def isValidEmail(email):
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log_security_event(user, action, ip_address, user_agent, success=True):
    SecurityLog.objects.create(
        user=user,
        action=action,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success
    )


@csrf_protect
@require_http_methods(["GET", "POST"])
def secure_register(request):
    if request.method == 'POST':
        form = SecureUserCreationForm(request.POST)
        
        # Логируем попытку регистрации
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.is_active = True  # Сразу активируем аккаунт для простоты
            user.save()
            
            # Создаем профиль пользователя
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            # Логируем успешную регистрацию
            log_security_event(user, 'register', ip_address, user_agent, True)
            
            messages.success(
                request, 
                'Регистрация успешна! Теперь вы можете войти в систему.'
            )
            return redirect('login')
        else:
            # Логируем неудачную попытку регистрации
            if hasattr(form, 'cleaned_data') and 'username' in form.cleaned_data:
                try:
                    user = User.objects.get(username=form.cleaned_data['username'])
                    log_security_event(user, 'register_failed', ip_address, user_agent, False)
                except User.DoesNotExist:
                    pass
            
    else:
        form = SecureUserCreationForm()
    
    return render(request, 'main/register.html', {'form': form})

def send_verification_email(user, request):
    verification_url = f"{request.scheme}://{request.get_host()}/verify-email/{user.verification_token}/"
    
    subject = "Подтверждение email - Техресурс"
    html_message = render_to_string('main/email_verification.html', {
        'user': user,
        'verification_url': verification_url,
    })
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )

@csrf_protect
@require_http_methods(["GET", "POST"])
def secure_login(request):
    if request.method == 'POST':
        form = SecureAuthenticationForm(data=request.POST, request=request)
        
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Логируем попытку входа
        LoginAttempt.objects.create(
            username=request.POST.get('username', ''),
            ip_address=ip_address,
            user_agent=user_agent,
            success=False
        )
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Обновляем попытку входа как успешную
                attempt = LoginAttempt.objects.filter(
                    username=username, 
                    ip_address=ip_address
                ).last()
                if attempt:
                    attempt.success = True
                    attempt.save()
                
                # Логируем успешный вход
                log_security_event(user, 'login', ip_address, user_agent, True)
                
                # Очищаем сессию от неудачных попыток
                if 'login_attempts' in request.session:
                    del request.session['login_attempts']
                
                messages.success(request, 'Вход выполнен успешно!')
                return redirect('profile')
        
        # Логируем неудачную попытку входа
        if form.cleaned_data.get('username'):
            try:
                user = User.objects.get(username=form.cleaned_data['username'])
                log_security_event(user, 'login_failed', ip_address, user_agent, False)
            except User.DoesNotExist:
                pass
        
        messages.error(request, 'Неверное имя пользователя или пароль.')
    
    else:
        form = SecureAuthenticationForm(request=request)
    
    return render(request, 'main/login.html', {'form': form})

@csrf_protect
@require_http_methods(["GET", "POST"])
def secure_password_reset(request):
    if request.method == 'POST':
        form = SecurePasswordResetForm(request.POST)
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        if form.is_valid():
            email = form.cleaned_data['email']
            
            try:
                user = User.objects.get(email=email, is_active=True)
                
                # Создаем токен сброса пароля
                token = secrets.token_urlsafe(32)
                expires_at = timezone.now() + timedelta(hours=1)
                
                PasswordResetToken.objects.create(
                    user=user,
                    token=token,
                    expires_at=expires_at,
                    ip_address=ip_address
                )
                
                # Отправляем email
                send_password_reset_email(user, token, request)
                
                # Логируем запрос сброса пароля
                log_security_event(user, 'password_reset_request', ip_address, user_agent, True)
                
            except User.DoesNotExist:
                pass
            
            # Всегда показываем одинаковое сообщение для безопасности
            messages.success(
                request, 
                'Если email зарегистрирован, инструкции по сбросу пароля будут отправлены.'
            )
            return redirect('login')
    
    else:
        form = SecurePasswordResetForm()
    
    return render(request, 'main/password_reset.html', {'form': form})

def send_password_reset_email(user, token, request):
    reset_url = f"{request.scheme}://{request.get_host()}/password-reset-confirm/{token}/"
    
    subject = "Сброс пароля - Техресурс"
    html_message = render_to_string('main/password_reset_email.html', {
        'user': user,
        'reset_url': reset_url,
    })
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )

@csrf_protect
@require_http_methods(["GET", "POST"])
def secure_password_reset_confirm(request, token):
    try:
        reset_token = PasswordResetToken.objects.get(
            token=token,
            used=False,
            expires_at__gt=timezone.now()
        )
    except PasswordResetToken.DoesNotExist:
        messages.error(request, 'Ссылка для сброса пароля недействительна или устарела.')
        return redirect('password_reset')
    
    if request.method == 'POST':
        form = SecureSetPasswordForm(request.POST)
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        if form.is_valid():
            # Устанавливаем новый пароль
            user = reset_token.user
            user.set_password(form.cleaned_data['password1'])
            user.save()
            
            # Помечаем токен как использованный
            reset_token.used = True
            reset_token.save()
            
            # Логируем смену пароля
            log_security_event(user, 'password_reset_success', ip_address, user_agent, True)
            
            # Отправляем уведомление о смене пароля
            send_password_change_notification(user, request)
            
            messages.success(request, 'Пароль успешно изменен! Теперь вы можете войти.')
            return redirect('login')
    
    else:
        form = SecureSetPasswordForm()
    
    return render(request, 'main/password_reset_confirm.html', {
        'form': form,
        'token': token
    })

def send_password_change_notification(user, request):
    ip_address = get_client_ip(request)
    
    subject = "Пароль изменен - Техресурс"
    html_message = render_to_string('main/password_change_notification.html', {
        'user': user,
        'ip_address': ip_address,
        'timestamp': timezone.now(),
    })
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )

@login_required
@require_http_methods(["GET", "POST"])
def secure_change_password(request):
    if request.method == 'POST':
        form = SecureSetPasswordForm(request.POST)
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        if form.is_valid():
            # Проверяем текущий пароль
            current_password = request.POST.get('current_password')
            if not request.user.check_password(current_password):
                messages.error(request, 'Текущий пароль неверен.')
                log_security_event(request.user, 'password_change_failed', ip_address, user_agent, False)
            else:
                # Устанавливаем новый пароль
                request.user.set_password(form.cleaned_data['password1'])
                request.user.save()
                
                # Обновляем сессию
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, request.user)
                
                # Логируем смену пароля
                log_security_event(request.user, 'password_change', ip_address, user_agent, True)
                
                # Отправляем уведомление
                send_password_change_notification(request.user, request)
                
                messages.success(request, 'Пароль успешно изменен!')
                return redirect('profile')
    
    else:
        form = SecureSetPasswordForm()
    
    return render(request, 'main/change_password.html', {'form': form})

def verify_email(request, token):
    try:
        user = User.objects.get(
            verification_token=token,
            verification_token_created__gt=timezone.now()-timedelta(hours=24)
        )
        
        # Проверяем наличие полей перед установкой
        if hasattr(user, 'email_verified'):
            user.email_verified = True
        user.is_active = True
        user.verification_token = ''
        user.save()
        
        messages.success(request, 'Email успешно подтвержден! Теперь вы можете войти.')
        return redirect('login')
        
    except User.DoesNotExist:
        messages.error(request, 'Ссылка подтверждения недействительна или устарела.')
        return redirect('register')
    
# ------------------------------------------- !!! --------------------------------------
@login_required
def debug_codes(request):
    """Страница для отладки - показывает последние коды восстановления"""
    if not request.user.is_staff:
        return redirect('index')
    
    profiles = UserProfile.objects.filter(
        sms_code__isnull=False,
        sms_code_expires__gt=timezone.now()
    ).select_related('user')
    
    return render(request, 'main/debug_codes.html', {'profiles': profiles})

# ------------------------------------------- !!! --------------------------------------


def send_contact_message(name, email, phone, message, ip_address):
    """Отправка сообщения обратной связи в Telegram"""
    try:
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID_CONTACTS:
            print("⚠️ TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID_CONTACTS не настроены")
            return False
        
            
        telegram_message = f"""
📩 <b>НОВОЕ СООБЩЕНИЕ ОБРАТНОЙ СВЯЗИ</b>

👤 <b>Имя:</b> {name}
📧 <b>Email:</b> {email}
📞 <b>Телефон:</b> {phone}
🌐 <b>IP-адрес:</b> {ip_address}

💬 <b>Сообщение:</b>
{message}
"""
        
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': settings.TELEGRAM_CHAT_ID_CONTACTS,
            'text': telegram_message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Ошибка отправки сообщения обратной связи: {e}")
        return False

@csrf_exempt
def contact_form_submit(request):
    """Обработка формы обратной связи"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            email = data.get('email', '').strip()
            phone = data.get('phone', '').strip()
            message = data.get('message', '').strip()
            
            # Валидация
            if not name or not message:
                return JsonResponse({
                    'success': False,
                    'error': 'Пожалуйста, заполните имя и сообщение'
                })
            
            if not email and not phone:
                return JsonResponse({
                    'success': False,
                    'error': 'Пожалуйста, укажите email или телефон для связи'
                })
            
            # Получаем IP-адрес
            ip_address = get_client_ip(request)
            
            # Отправляем в Telegram
            success = send_contact_message(name, email, phone, message, ip_address)
            
            if success:
                # Логируем успешную отправку
                NotificationLog.objects.create(
                    notification_type='email_sent',
                    message=f'Сообщение обратной связи от {name}',
                    sent_to=f"Telegram: {settings.TELEGRAM_CHAT_ID_CONTACTS}",
                    success=True
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Сообщение успешно отправлено! Мы свяжемся с вами в ближайшее время.'
                })
            else:
                # Логируем ошибку
                NotificationLog.objects.create(
                    notification_type='email_sent',
                    message=f'Ошибка отправки сообщения от {name}',
                    sent_to=f"Telegram: {settings.TELEGRAM_CHAT_ID_CONTACTS}",
                    success=False,
                    error_message='Ошибка Telegram API'
                )
                
                return JsonResponse({
                    'success': False,
                    'error': 'Ошибка при отправке сообщения. Попробуйте позже.'
                })
                
        except Exception as e:
            print(f"❌ Ошибка обработки формы: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Произошла ошибка. Попробуйте еще раз.'
            })
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

