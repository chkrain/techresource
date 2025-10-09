# main/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.utils.html import strip_tags
from django.contrib.admin.views.decorators import staff_member_required
import datetime
import json
import hashlib
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Min, Max
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

from .models import Product, Cart, CartItem, Order, OrderItem, UserProfile, Address, NotificationLog, SecurityLog, PasswordResetToken, LoginAttempt, OrderStatusLog, WishlistItem, Wishlist, ProductReview
from .forms import SecureUserCreationForm, SecureAuthenticationForm, SecurePasswordResetForm, SecureSetPasswordForm, UserRegisterForm, UserProfileForm, AddressForm, ProductReviewForm


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

@staff_member_required
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
    
    # Отзывы на модерации
    pending_reviews = ProductReview.objects.filter(
        is_moderated=False
    ).select_related('user', 'product').order_by('-created_at')
    
    pending_reviews_count = pending_reviews.count()
    
    context = {
        'orders': orders,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'paid_orders': paid_orders,
        'total_revenue': total_revenue,
        'status_choices': Order.STATUS_CHOICES,
        'selected_status': status_filter,
        'selected_date': date_filter,
        'pending_reviews': pending_reviews,
        'pending_reviews_count': pending_reviews_count,
    }
    
    return render(request, 'main/admin_dashboard.html', context)

@staff_member_required
def moderate_review(request, review_id):
    """Модерация отзыва"""
    review = get_object_or_404(ProductReview, id=review_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            review.is_approved = True
            review.is_moderated = True
            review.save()
            messages.success(request, f'Отзыв от {review.user.username} одобрен')
            
        elif action == 'reject':
            review.is_approved = False
            review.is_moderated = True
            review.save()
            messages.success(request, f'Отзыв от {review.user.username} отклонен')
    
    return redirect('admin_dashboard')

def products(request):
    # Параметры поиска
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    brand_filter = request.GET.get('brand', '')
    price_min = request.GET.get('price_min', '')
    price_max = request.GET.get('price_max', '')
    in_stock = request.GET.get('in_stock', '')
    sort_by = request.GET.get('sort_by', 'name')
    
    # Получаем товары
    products_list = Product.objects.filter(is_active=True)
    
    # Применяем фильтры
    if search_query:
        products_list = products_list.filter(
            Q(name__icontains=search_query) |
            Q(article__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(material__icontains=search_query)
        )
    
    if category_filter:
        products_list = products_list.filter(category=category_filter)
    
    if brand_filter:
        products_list = products_list.filter(brand=brand_filter)
    
    if price_min:
        try:
            products_list = products_list.filter(price__gte=float(price_min))
        except ValueError:
            pass
    
    if price_max:
        try:
            products_list = products_list.filter(price__lte=float(price_max))
        except ValueError:
            pass
    
    if in_stock == 'true':
        products_list = products_list.filter(quantity__gt=0)
    
    # Применяем сортировку
    sort_options = {
        'name': 'name',
        'price_asc': 'price',
        'price_desc': '-price',
        'popularity': '-popularity',
        'rating': '-rating',
        'newest': '-created_at',
        'quantity': '-quantity'
    }
    products_list = products_list.order_by(sort_options.get(sort_by, 'name'))
    
    # Пагинация
    paginator = Paginator(products_list, 12)  # 12 товаров на страницу
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Получаем доступные фильтры
    categories = Product.objects.filter(is_active=True).values_list('category', flat=True).distinct()
    brands = Product.objects.filter(is_active=True).values_list('brand', flat=True).distinct()
    
    # Получаем минимальную и максимальную цены
    price_range = products_list.aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )
    
    # Добавляем информацию об избранном
    if request.user.is_authenticated:
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            wishlist_product_ids = wishlist.wishlistitem_set.values_list('product_id', flat=True)
            
            for product in page_obj:
                product.in_wishlist = product.id in wishlist_product_ids
                product.average_rating = ProductReview.get_average_rating(product)
                product.reviews_count = ProductReview.get_approved_reviews(product).count()
        except Wishlist.DoesNotExist:
            for product in page_obj:
                product.in_wishlist = False
    else:
        for product in page_obj:
            product.in_wishlist = False
    
    # Похожие товары
    similar_products = None
    if search_query:
        found_categories = products_list.values_list('category', flat=True).distinct()
        if found_categories:
            similar_products = Product.objects.filter(
                is_active=True,
                category__in=found_categories
            ).exclude(
                id__in=products_list.values_list('id', flat=True)
            )[:6]
    
    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'similar_products': similar_products,
        'categories': categories,
        'brands': brands,
        'search_query': search_query,
        'selected_category': category_filter,
        'selected_brand': brand_filter,
        'price_min': price_min,
        'price_max': price_max,
        'in_stock': in_stock,
        'sort_by': sort_by,
        'price_range': price_range,
        'filter_params': request.GET.copy(),
    }
    
    # Если AJAX запрос, возвращаем JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.template.loader import render_to_string
        
        # Создаем контекст для рендеринга товаров
        product_context = {
            'products': page_obj,
            'page_obj': page_obj,
        }
        
        products_html = render_to_string('main/components/product_grid.html', product_context)
        
        return JsonResponse({
            'success': True,
            'products_html': products_html,
            'has_next': page_obj.has_next(),
            'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            'total_count': paginator.count,
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
        })
    
    return render(request, 'main/products.html', context)

def get_price_range(request):
    """API для получения минимальной и максимальной цены"""
    category = request.GET.get('category', '')
    brand = request.GET.get('brand', '')
    
    products = Product.objects.filter(is_active=True)
    
    if category:
        products = products.filter(category=category)
    if brand:
        products = products.filter(brand=brand)
    
    price_range = products.aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )
    
    return JsonResponse({
        'min_price': float(price_range['min_price'] or 0),
        'max_price': float(price_range['max_price'] or 10000)
    })

def search_suggestions(request):
    """API для подсказок поиска"""
    query = request.GET.get('q', '')
    suggestions = []
    
    if len(query) >= 2:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(article__icontains=query) |
            Q(category__icontains=query),
            is_active=True
        ).distinct()[:10]
        
        for product in products:
            suggestions.append({
                'name': product.name,
                'category': product.category,
                'article': product.article
            })
    
    return JsonResponse({'suggestions': suggestions})

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
    if request.method == 'POST':
        try:
            product = Product.objects.get(id=product_id)
            cart, created = Cart.objects.get_or_create(user=request.user)
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            
            if not created:
                cart_item.quantity += 1
                cart_item.save()
            
            cart_count = cart.get_items_count()
            
            return JsonResponse({
                'success': True,
                'cart_count': cart_count,
                'message': 'Товар добавлен в корзину'
            })
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Товар не найден'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
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
    payment_status = None
    payment_info = None
    
    try:
        if order.payment_id:
            payment = Payment.find_one(order.payment_id)
            payment_status = payment.status
            payment_info = {
                'id': payment.id,
                'amount': payment.amount.value,
                'currency': payment.amount.currency,
                'created_at': payment.created_at,
                'description': getattr(payment, 'description', '')
            }
            
            print(f"🔍 Статус платежа для заказа #{order_id}: {payment_status}")
            
            if payment_status == 'succeeded':
                if order.status != 'paid':
                    order.status = 'paid'
                    order.paid_at = timezone.now()
                    order.save()
                    
                    # Уменьшаем количество товаров
                    for item in order.orderitem_set.all():
                        if item.product.quantity >= item.quantity:
                            item.product.quantity -= item.quantity
                            item.product.save()
                    
                    send_order_notification(order)
                    messages.success(request, '✅ Оплата прошла успешно! Заказ подтвержден.')
                    
            elif payment_status == 'canceled':
                if order.status != 'cancelled':
                    order.status = 'cancelled'
                    order.save()
                    messages.error(request, '❌ Платеж был отменен.')
                    
            elif payment_status == 'pending':
                messages.info(request, '⏳ Платеж обрабатывается. Мы уведомим вас, когда он будет завершен.')
                
            else:
                messages.warning(request, f'ℹ️ Статус платежа: {payment_status}')
                
    except Exception as e:
        print(f"❌ Ошибка при проверке платежа: {e}")
        messages.error(request, '⚠️ Не удалось проверить статус платежа. Пожалуйста, свяжитесь с поддержкой.')
    
    context = {
        'order': order,
        'payment_status': payment_status,
        'payment_info': payment_info
    }
    
    # Если платеж отменен, перенаправляем на страницу неудачи
    if payment_status == 'canceled':
        return redirect('payment_failed', order_id=order.id)
    
    return render(request, 'main/payment_success.html', context)

@login_required
def retry_payment(request, order_id):
    """Повторная попытка оплаты для отмененного заказа"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Проверяем, можно ли повторить оплату
    if order.status not in ['pending', 'cancelled']:
        messages.error(request, 'Невозможно повторить оплату для этого заказа.')
        return redirect('orders')
    
    try:
        # Создаем новый платеж
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
            "description": f"Повторная оплата заказа #{order.id}",
            "metadata": {
                "order_id": order.id,
                "user_id": request.user.id
            }
        }, str(uuid.uuid4()))
        
        # Обновляем ID платежа в заказе
        order.payment_id = payment.id
        order.status = 'pending'  # Сбрасываем статус
        order.save()
        
        # Перенаправляем на страницу оплаты ЮКассы
        return redirect(payment.confirmation.confirmation_url)
        
    except Exception as e:
        messages.error(request, f'❌ Ошибка при создании платежа: {str(e)}')
        return redirect('orders')

@login_required
def update_order_payment_method(request, order_id):
    """Смена способа оплаты заказа"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method == 'POST':
        new_payment_method = request.POST.get('payment_method')
        
        if new_payment_method in ['card', 'invoice']:
            order.payment_method = new_payment_method
            
            if new_payment_method == 'invoice':
                order.status = 'processing'
                send_invoice_order_notification(order)
                messages.success(request, 'Заказ переведен на оплату по счету. Мы вышлем счет на вашу почту.')
            else:
                order.status = 'pending'
                messages.success(request, 'Способ оплаты изменен на банковскую карту.')
            
            order.save()
            
            # Логируем изменение
            OrderStatusLog.objects.create(
                order=order,
                old_status=order.status,
                new_status=order.status,
                changed_by=request.user,
                notes=f"Изменен способ оплаты на {order.get_payment_method_display()}"
            )
        else:
            messages.error(request, 'Неверный способ оплаты.')
    
    return redirect('orders')

@csrf_exempt
def yookassa_webhook(request):
    """Webhook для уведомлений от ЮКассы"""
    if request.method == 'POST':
        try:
            event_json = json.loads(request.body.decode('utf-8'))
            event_type = event_json.get('event')
            
            print(f"🔔 Webhook получен: {event_type}")
            
            if event_type == 'payment.succeeded':
                return handle_successful_payment(event_json)
            elif event_type == 'payment.canceled':
                return handle_canceled_payment(event_json)
            elif event_type == 'payment.waiting_for_capture':
                return handle_pending_payment(event_json)
            elif event_type == 'refund.succeeded':
                return handle_refund(event_json)
            else:
                print(f"⚠️ Неизвестный тип события: {event_type}")
                return JsonResponse({'status': 'unknown_event'})
                
        except Exception as e:
            print(f"❌ Ошибка в webhook: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'method not allowed'}, status=405)

def handle_successful_payment(event_json):
    """Обработка успешного платежа"""
    payment_id = event_json['object']['id']
    
    try:
        order = Order.objects.get(payment_id=payment_id)
        
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
                    print(f"⚠️ Недостаточно товара {item.product.name} для заказа #{order.id}")
            
            # Отправляем уведомления
            send_order_notification(order)
            
            # Логируем
            NotificationLog.objects.create(
                order=order,
                notification_type='payment_success',
                message=f'Заказ #{order.id} оплачен через webhook',
                sent_to=order.customer_email,
                success=True
            )
            
            print(f"✅ Заказ #{order.id} оплачен через webhook")
        
        return JsonResponse({'status': 'success'})
        
    except Order.DoesNotExist:
        print(f"❌ Заказ с payment_id {payment_id} не найден")
        return JsonResponse({'status': 'order_not_found'}, status=404)

def handle_canceled_payment(event_json):
    """Обработка отмененного платежа"""
    payment_id = event_json['object']['id']
    
    try:
        order = Order.objects.get(payment_id=payment_id)
        
        if order.status != 'cancelled':
            order.status = 'cancelled'
            order.cancelled_at = timezone.now()
            order.save()
            
            # Логируем
            NotificationLog.objects.create(
                order=order,
                notification_type='payment_cancelled',
                message=f'Платеж для заказа #{order.id} отменен',
                sent_to=order.customer_email,
                success=True
            )
            
            print(f"❌ Платеж для заказа #{order.id} отменен")
        
        return JsonResponse({'status': 'cancelled'})
        
    except Order.DoesNotExist:
        print(f"❌ Заказ с payment_id {payment_id} не найден")
        return JsonResponse({'status': 'order_not_found'}, status=404)

def handle_pending_payment(event_json):
    """Обработка платежа, ожидающего подтверждения"""
    payment_id = event_json['object']['id']
    
    try:
        order = Order.objects.get(payment_id=payment_id)
        
        # Можно добавить логику для платежей, требующих подтверждения
        print(f"⏳ Платеж для заказа #{order.id} ожидает подтверждения")
        
        return JsonResponse({'status': 'pending'})
        
    except Order.DoesNotExist:
        print(f"❌ Заказ с payment_id {payment_id} не найден")
        return JsonResponse({'status': 'order_not_found'}, status=404)

def handle_refund(event_json):
    """Обработка возврата средств"""
    payment_id = event_json['object']['payment_id']
    
    try:
        order = Order.objects.get(payment_id=payment_id)
        
        if order.status != 'refunded':
            order.status = 'refunded'
            order.save()
            
            # Возвращаем товары на склад
            for item in order.orderitem_set.all():
                item.product.quantity += item.quantity
                item.product.save()
            
            # Логируем
            NotificationLog.objects.create(
                order=order,
                notification_type='refund_processed',
                message=f'Возврат средств для заказа #{order.id}',
                sent_to=order.customer_email,
                success=True
            )
            
            print(f"💰 Возврат средств для заказа #{order.id}")
        
        return JsonResponse({'status': 'refunded'})
        
    except Order.DoesNotExist:
        print(f"❌ Заказ с payment_id {payment_id} не найден")
        return JsonResponse({'status': 'order_not_found'}, status=404)

@login_required
@require_http_methods(["POST"])
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Проверяем, является ли запрос AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    try:
        if order.can_be_cancelled():
            old_status = order.status
            order.status = 'cancelled'
            order.cancelled_at = timezone.now()
            order.save()
            
            # Возвращаем товары на склад
            for item in order.orderitem_set.all():
                item.product.quantity += item.quantity
                item.product.save()
            
            # Создаем лог изменения статуса
            OrderStatusLog.objects.create(
                order=order,
                old_status=old_status,
                new_status='cancelled',
                changed_by=request.user,
                notes="Отменен пользователем через сайт"
            )
            
            # Отправляем уведомление об отмене в Telegram
            send_cancellation_notification(order)
            
            # Логируем уведомление
            NotificationLog.objects.create(
                order=order,
                notification_type='order_cancelled',
                message=f'Заказ #{order.id} отменен пользователем',
                sent_to=f"Telegram: {settings.TELEGRAM_CHAT_ID}",
                success=True
            )
            
            message = f'Заказ #{order.id} отменен. Уведомление отправлено администратору.'
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': message
                })
            else:
                messages.success(request, message)
                
        else:
            message = 'Невозможно отменить заказ. Срок отмены истек или заказ уже обрабатывается. Если возникли вопросы - свяжитесь с нами, мы поможем!'
            
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'error': message
                })
            else:
                messages.error(request, message)
                
    except Exception as e:
        error_msg = f'Ошибка при отмене заказа: {str(e)}'
        print(f"❌ Ошибка отмены заказа #{order_id}: {e}")
        
        if is_ajax:
            return JsonResponse({
                'success': False,
                'error': error_msg
            })
        else:
            messages.error(request, error_msg)
    
    if not is_ajax:
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
    """Отправка уведомления об отмене заказа в Telegram"""
    try:
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            print("⚠️ TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не настроены")
            return False
            
        message = f"""
❌ <b>ЗАКАЗ ОТМЕНЕН #{order.id}</b>
        
👤 <b>Клиент:</b> {order.customer_name}
📞 <b>Телефон:</b> {order.customer_phone}
📧 <b>Email:</b> {order.customer_email}
💰 <b>Сумма:</b> {order.total_price} руб.
🚚 <b>Адрес:</b> {order.delivery_address}
🕒 <b>Время отмены:</b> {timezone.now().strftime('%d.%m.%Y %H:%M')}

<b>Товары:</b>
"""
        
        for item in order.orderitem_set.all():
            message += f"• {item.product.name} x{item.quantity} - {item.get_total_price()} руб.\n"
        
        message += f"\n<b>Итого:</b> {order.total_price} руб."
        message += f"\n\n⚠️ <b>Требуется вернуть средства клиенту</b>"
        
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

@staff_member_required
def update_order_status(request, order_id=None):
    """Обновление статуса заказа (для админов)"""
    # Если order_id не передан в URL, берем из POST данных
    if not order_id:
        order_id = request.POST.get('order_id')
    
    if not order_id:
        messages.error(request, 'ID заказа не указан')
        return redirect('admin_dashboard')
    
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        messages.error(request, f'Заказ #{order_id} не найден')
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        tracking_number = request.POST.get('tracking_number', '')
        shipping_company = request.POST.get('shipping_company', '')
        estimated_delivery = request.POST.get('estimated_delivery', '')
        notes = request.POST.get('notes', '')
        
        if new_status and new_status in dict(Order.STATUS_CHOICES):
            old_status = order.status
            
            # Создаем лог изменения
            OrderStatusLog.objects.create(
                order=order,
                old_status=old_status,
                new_status=new_status,
                changed_by=request.user,
                notes=notes
            )
            
            # Обновляем заказ
            order.status = new_status
            order.status_changed_at = timezone.now()
            
            if tracking_number:
                order.tracking_number = tracking_number
            if shipping_company:
                order.shipping_company = shipping_company
            if estimated_delivery:
                try:
                    # ИСПРАВЛЕНИЕ: используем правильный импорт datetime
                    from datetime import datetime
                    order.estimated_delivery = datetime.strptime(estimated_delivery, '%Y-%m-%d').date()
                except ValueError:
                    pass
                
            order.save()
            
            # Отправляем уведомление
            send_order_status_notification(order, old_status, new_status)
            
            messages.success(request, f'Статус заказа #{order.id} обновлен на "{order.get_status_display()}"')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'new_status': order.get_status_display(),
                    'timeline': order.get_current_timeline()
                })
        else:
            messages.error(request, 'Неверный статус заказа')
        
        return redirect('admin_dashboard')
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
def get_order_timeline(request, order_id):
    """API для получения временной шкалы заказа"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    return JsonResponse({
        'timeline': order.get_current_timeline(),
        'tracking_info': {
            'tracking_number': order.tracking_number,
            'shipping_company': order.shipping_company,
            'estimated_delivery': order.estimated_delivery.isoformat() if order.estimated_delivery else None
        }
    })

def send_order_status_notification(order, old_status, new_status):
    """Отправка уведомления об изменении статуса"""
    try:
        # Уведомление в Telegram для админов
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            message = f"""
🔄 <b>ИЗМЕНЕНИЕ СТАТУСА ЗАКАЗА #{order.id}</b>

📊 <b>Статус:</b> {dict(Order.STATUS_CHOICES)[old_status]} → {dict(Order.STATUS_CHOICES)[new_status]}
👤 <b>Клиент:</b> {order.customer_name}
📞 <b>Телефон:</b> {order.customer_phone}
💰 <b>Сумма:</b> {order.total_price} руб.

⏰ <b>Время:</b> {timezone.now().strftime('%d.%m.%Y %H:%M')}
"""
            
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': settings.TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            }
            requests.post(url, json=payload, timeout=10)
            
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления о статусе: {e}")

def send_refund_request_notification(order, reason):
    """Уведомление о запросе возврата"""
    try:
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            message = f"""
            💰 <b>ЗАПРОС ВОЗВРАТА СРЕДСТВ</b>

            🆔 <b>Заказ:</b> #{order.id}
            👤 <b>Клиент:</b> {order.customer_name}
            📞 <b>Телефон:</b> {order.customer_phone}
            💳 <b>Сумма:</b> {order.total_price} руб.

            📝 <b>Причина:</b> {reason}

            ⏰ <b>Время запроса:</b> {timezone.now().strftime('%d.%m.%Y %H:%M')}
            """
            
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': settings.TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            }
            requests.post(url, json=payload, timeout=10)
            
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления о возврате: {e}")


def send_order_status_email(order, old_status, new_status):
    """Отправка email уведомления клиенту"""
    try:
        subject = f"Статус вашего заказа #{order.id} обновлен - Техресурс"
        
        context = {
            'order': order,
            'old_status': dict(Order.STATUS_CHOICES)[old_status],
            'new_status': dict(Order.STATUS_CHOICES)[new_status],
            'timeline': order.get_current_timeline(),
        }
        
        html_message = render_to_string('main/order_status_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [order.customer_email],
            html_message=html_message,
            fail_silently=False,
        )
        
    except Exception as e:
        print(f"❌ Ошибка отправки email о статусе: {e}")

@login_required
def request_order_refund(request, order_id):
    """Запрос на возврат средств"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        # Можно добавить дополнительные проверки
        if order.status in ['paid', 'completed']:
            order.status = 'refunded'
            order.save()
            
            # Логируем запрос возврата
            OrderStatusLog.objects.create(
                order=order,
                old_status=order.status,
                new_status='refunded',
                notes=f"Запрос возврата: {reason}"
            )
            
            # Уведомление админов
            send_refund_request_notification(order, reason)
            
            messages.success(request, 'Запрос на возврат отправлен. Мы свяжемся с вами для уточнения деталей.')
        else:
            messages.error(request, 'Невозможно оформить возврат для заказа с текущим статусом.')
    
    return redirect('orders')

@login_required
def payment_failed(request, order_id):
    """Страница неудачной оплаты"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Получаем информацию о платеже
    payment_info = None
    try:
        if order.payment_id:
            payment = Payment.find_one(order.payment_id)
            payment_info = {
                'status': payment.status,
                'cancellation_reason': getattr(payment, 'cancellation_details', {}).get('reason', 'Неизвестно'),
                'description': getattr(payment, 'description', '')
            }
    except Exception as e:
        print(f"❌ Ошибка получения информации о платеже: {e}")
    
    context = {
        'order': order,
        'payment_info': payment_info
    }
    return render(request, 'main/payment_failed.html', context)

# main/views.py (добавить в конец файла)

def handler404(request, exception):
    """Кастомная страница 404 ошибки"""
    context = {
        'error_code': '404',
        'error_title': 'Страница не найдена',
        'error_message': 'Запрашиваемая страница не существует или была перемещена',
        'suggestions': [
            'Проверьте правильность введенного URL-адреса',
            'Вернитесь на главную страницу',
            'Воспользуйтесь поиском по сайту',
            'Свяжитесь с нашей поддержкой, если проблема повторяется'
        ]
    }
    return render(request, 'main/error.html', context, status=404)

def handler500(request):
    """Кастомная страница 500 ошибки"""
    context = {
        'error_code': '500',
        'error_title': 'Внутренняя ошибка сервера',
        'error_message': 'Произошла внутренняя ошибка сервера. Мы уже работаем над ее устранением',
        'suggestions': [
            'Обновите страницу через несколько минут',
            'Попробуйте очистить кэш браузера',
            'Вернитесь на главную страницу',
            'Сообщите о проблеме в службу поддержки'
        ]
    }
    return render(request, 'main/error.html', context, status=500)

def handler403(request, exception):
    """Кастомная страница 403 ошибки"""
    context = {
        'error_code': '403',
        'error_title': 'Доступ запрещен',
        'error_message': 'У вас недостаточно прав для доступа к этой странице',
        'suggestions': [
            'Проверьте, авторизованы ли вы в системе',
            'Обратитесь к администратору для получения доступа',
            'Вернитесь на главную страницу',
            'Войдите под другой учетной записью'
        ]
    }
    return render(request, 'main/error.html', context, status=403)

def handler400(request, exception):
    """Кастомная страница 400 ошибки"""
    context = {
        'error_code': '400',
        'error_title': 'Неверный запрос',
        'error_message': 'Сервер не может обработать ваш запрос из-за неверного синтаксиса',
        'suggestions': [
            'Проверьте корректность введенных данных',
            'Обновите страницу и попробуйте снова',
            'Очистите cookies и кэш браузера',
            'Свяжитесь с поддержкой, если проблема не решается'
        ]
    }
    return render(request, 'main/error.html', context, status=400)

@login_required
def toggle_wishlist(request, product_id):
    """Добавление/удаление товара в избранное"""
    if request.method == 'POST':
        try:
            product = Product.objects.get(id=product_id, is_active=True)
            wishlist, created = Wishlist.objects.get_or_create(user=request.user)
            
            # Проверяем, есть ли уже товар в избранном
            wishlist_item = WishlistItem.objects.filter(
                wishlist=wishlist, 
                product=product
            ).first()
            
            if wishlist_item:
                # Удаляем из избранного
                wishlist_item.delete()
                action = 'removed'
                message = 'Товар удален из избранного'
            else:
                # Добавляем в избранное
                WishlistItem.objects.create(wishlist=wishlist, product=product)
                action = 'added'
                message = 'Товар добавлен в избранное'
            
            # Получаем обновленное количество
            wishlist_count = wishlist.get_items_count()
            
            return JsonResponse({
                'success': True,
                'action': action,
                'message': message,
                'wishlist_count': wishlist_count,
                'product_id': product_id
            })
            
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Товар не найден'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
def wishlist_view(request):
    """Страница избранных товаров"""
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    wishlist_items = WishlistItem.objects.filter(wishlist=wishlist).select_related('product')
    
    context = {
        'wishlist': wishlist,
        'wishlist_items': wishlist_items,
    }
    return render(request, 'main/wishlist.html', context)

@login_required
def wishlist_to_cart(request, product_id):
    """Перенос товара из избранного в корзину"""
    if request.method == 'POST':
        try:
            product = Product.objects.get(id=product_id, is_active=True)
            wishlist = Wishlist.objects.get(user=request.user)
            
            # Удаляем из избранного
            WishlistItem.objects.filter(wishlist=wishlist, product=product).delete()
            
            # Добавляем в корзину
            cart, created = Cart.objects.get_or_create(user=request.user)
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            
            if not created:
                cart_item.quantity += 1
                cart_item.save()
            
            # Получаем обновленные данные
            cart_count = cart.cartitem_set.count()
            wishlist_count = wishlist.get_items_count()
            
            return JsonResponse({
                'success': True,
                'message': 'Товар перемещен в корзину',
                'cart_count': cart_count,
                'wishlist_count': wishlist_count,
                'product_id': product_id
            })
            
        except (Product.DoesNotExist, Wishlist.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': 'Товар не найден'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
def remove_from_wishlist(request, product_id):
    """Удаление товара из избранного"""
    if request.method == 'POST':
        try:
            product = Product.objects.get(id=product_id)
            wishlist = Wishlist.objects.get(user=request.user)
            
            # Удаляем из избранного
            deleted_count = WishlistItem.objects.filter(
                wishlist=wishlist, 
                product=product
            ).delete()[0]
            
            wishlist_count = wishlist.get_items_count()
            
            return JsonResponse({
                'success': True,
                'message': 'Товар удален из избранного',
                'wishlist_count': wishlist_count,
                'product_id': product_id
            })
            
        except (Product.DoesNotExist, Wishlist.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': 'Товар не найден'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
def clear_wishlist(request):
    """Очистка всего избранного"""
    if request.method == 'POST':
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            deleted_count = WishlistItem.objects.filter(wishlist=wishlist).delete()[0]
            
            return JsonResponse({
                'success': True,
                'message': f'Избранное очищено ({deleted_count} товаров удалено)',
                'wishlist_count': 0
            })
            
        except Wishlist.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Избранное не найдено'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

# main/views.py
def product_detail(request, product_id):
    """Детальная страница товара"""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # Получаем похожие товары
    similar_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id)[:4]
    
    # Проверяем, есть ли товар в избранном у текущего пользователя
    in_wishlist = False
    if request.user.is_authenticated:
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            in_wishlist = WishlistItem.objects.filter(
                wishlist=wishlist, 
                product=product
            ).exists()
        except Wishlist.DoesNotExist:
            pass
    
    context = {
        'product': product,
        'similar_products': similar_products,
        'in_wishlist': in_wishlist,
    }
    
    return render(request, 'main/product_detail.html', context)

@login_required
def add_review(request, product_id):
    """Добавление отзыва к товару"""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # Проверяем, может ли пользователь оставить отзыв
    if not ProductReview.can_user_review(request.user, product):
        messages.error(request, 'Вы не можете оставить отзыв на этот товар.')
        return redirect('product_detail', product_id=product_id)
    
    if request.method == 'POST':
        form = ProductReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.is_moderated = False
            review.is_approved = False
            
            review.save()
            messages.success(request, 'Спасибо за ваш отзыв!')
            return redirect('product_detail', product_id=product_id)
    else:
        form = ProductReviewForm()
    
    context = {
        'form': form,
        'product': product,
    }
    return render(request, 'main/add_review.html', context)

@login_required
def edit_review(request, review_id):
    """Редактирование отзыва"""
    review = get_object_or_404(ProductReview, id=review_id, user=request.user)
    
    if request.method == 'POST':
        form = ProductReviewForm(request.POST, instance=review)
        if form.is_valid():
            # Сбрасываем модерацию при редактировании
            review = form.save(commit=False)
            review.is_moderated = False
            review.is_approved = False
            review.save()
            
            messages.success(request, 'Отзыв обновлен и отправлен на модерацию.')
            return redirect('product_detail', product_id=review.product.id)
    else:
        form = ProductReviewForm(instance=review)
    
    context = {
        'form': form,
        'review': review,
        'product': review.product,
    }
    return render(request, 'main/add_review.html', context)

@login_required
def delete_review(request, review_id):
    """Удаление отзыва"""
    review = get_object_or_404(ProductReview, id=review_id, user=request.user)
    product_id = review.product.id
    
    if request.method == 'POST':
        review.delete()
        messages.success(request, 'Отзыв удален.')
        return redirect('product_detail', product_id=product_id)
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

# Обновим функцию product_detail для включения отзывов
def product_detail(request, product_id):
    """Детальная страница товара"""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # Получаем похожие товары
    similar_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id)[:4]
    
    # Проверяем, есть ли товар в избранном у текущего пользователя
    in_wishlist = False
    if request.user.is_authenticated:
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            in_wishlist = WishlistItem.objects.filter(
                wishlist=wishlist, 
                product=product
            ).exists()
        except Wishlist.DoesNotExist:
            pass
    
    # Получаем отзывы с пагинацией
    reviews_list = ProductReview.get_approved_reviews(product)
    paginator = Paginator(reviews_list, 5)  # 5 отзывов на страницу
    page = request.GET.get('page')
    
    try:
        reviews = paginator.page(page)
    except PageNotAnInteger:
        reviews = paginator.page(1)
    except EmptyPage:
        reviews = paginator.page(paginator.num_pages)
    
    # Средний рейтинг
    average_rating = ProductReview.get_average_rating(product)
    
    # Может ли пользователь оставить отзыв
    can_review = False
    user_review = None
    if request.user.is_authenticated:
        can_review = ProductReview.can_user_review(request.user, product)
        user_review = ProductReview.objects.filter(
            user=request.user, 
            product=product
        ).first()
    
    # Форма для отзыва (если нужно)
    review_form = ProductReviewForm() if can_review else None
    
    context = {
        'product': product,
        'similar_products': similar_products,
        'in_wishlist': in_wishlist,
        'reviews': reviews,
        'average_rating': average_rating,
        'can_review': can_review,
        'user_review': user_review,
        'review_form': review_form,
    }
    
    return render(request, 'main/product_detail.html', context)

@login_required
def reorder_order(request, order_id):
    """Повторение заказа - добавление всех товаров в корзину"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    try:
        cart, created = Cart.objects.get_or_create(user=request.user)
        added_count = 0
        
        # Добавляем все товары из заказа в корзину
        for order_item in order.orderitem_set.all():
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=order_item.product
            )
            
            if created:
                cart_item.quantity = order_item.quantity
            else:
                cart_item.quantity += order_item.quantity
            
            # Проверяем доступное количество
            if cart_item.quantity > cart_item.product.quantity:
                cart_item.quantity = cart_item.product.quantity
            
            cart_item.save()
            added_count += 1
        
        cart_count = cart.get_items_count()
        
        return JsonResponse({
            'success': True,
            'message': f'{added_count} товаров добавлено в корзину',
            'cart_count': cart_count,
            'added_count': added_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при повторении заказа: {str(e)}'
        })

@login_required
def order_details(request, order_id):
    """Детальная информация о заказе"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Получаем полную историю статусов
    status_logs = OrderStatusLog.objects.filter(order=order).order_by('-changed_at')
    
    # Получаем дополнительные данные
    context = {
        'order': order,
        'status_logs': status_logs,
        'order_items': order.orderitem_set.all(),
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.template.loader import render_to_string
        
        html = render_to_string('main/components/order_details_full.html', context)
        
        return JsonResponse({
            'success': True,
            'html': html
        })
    
    return render(request, 'main/order_details.html', context)

def contacts(request):
    """Страница контактов"""
    return render(request, 'main/contacts.html')

def service_design(request):
    """Страница услуги - Проектирование систем"""
    return render(request, 'main/service_design.html')

def service_electrical(request):
    """Страница услуги - Электромонтажные работы"""
    return render(request, 'main/service_electrical.html')

def service_software(request):
    """Страница услуги - Разработка ПО и SCADA"""
    return render(request, 'main/service_software.html')

def service_equipment(request):
    """Страница услуги - Поставка оборудования"""
    return render(request, 'main/service_equipment.html')

def service_support(request):
    """Страница услуги - Техническая поддержка"""
    return render(request, 'main/service_support.html')

def service_maintenance(request):
    """Страница услуги - Сервисное обслуживание"""
    return render(request, 'main/service_maintenance.html')