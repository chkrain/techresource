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
import secrets
from django.views.decorators.csrf import ensure_csrf_cookie
import hmac
from decimal import Decimal
import requests
from .models import NotificationLog
import uuid
import time
from .services.delivery_service import DeliveryService
import base64
from io import BytesIO
from django.contrib.auth.decorators import user_passes_test
from django.core.cache import cache
from hashlib import sha256
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import random
from datetime import timedelta, datetime
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
import os
from django.http import Http404
import magic
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import SupportTicket, SupportAttachment
from .forms import SupportTicketForm
from .forms import SecureUserCreationForm, SecureAuthenticationForm, SecurePasswordResetForm, SecureSetPasswordForm

from .models import Product, Cart, CartItem, Order, OrderItem, UserProfile, Address, NotificationLog, SecurityLog, PasswordResetToken, LoginAttempt, OrderStatusLog, WishlistItem, Wishlist, ProductReview, Admin2FA, ServicePage
from .forms import SecureUserCreationForm, SecureAuthenticationForm, SecurePasswordResetForm, SecureSetPasswordForm, UserRegisterForm, UserProfileForm, AddressForm, ProductReviewForm


from django.db.models import Sum

User = get_user_model()

def index(request):
    featured_products = Product.objects.filter(is_active=True, quantity__gt=0)[:6]  
    return render(request, 'main/index.html', {'featured_products': featured_products})

def about(request):
    return render(request, 'main/about.html')

def services(request):
    return render(request, 'main/services.html')

def privacy_policy(request):
    return render(request, 'main/privacy.html')

def altyshevo_instruction(request):
    """Отображение инструкции Алтышево"""
    return render(request, 'main/instructions/altyshevo_instruction.html')

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
    paid_orders = Order.objects.filter(is_payment_finalized=True).count()
    
    # Выручка (только оплаченные заказы)
    total_revenue = Order.objects.filter(status='paid').aggregate(
        total=Sum('final_price')
    )['total'] or 0

    total_gross = Order.objects.filter(is_payment_finalized=True).aggregate(
        total=Sum('paid_amount')
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
        'total_gross': total_gross,  
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

@ensure_csrf_cookie
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
            'user': request.user, 
            'request': request,  
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
            
            user = authenticate(
                request, 
                username=user.username,  
                password=form.cleaned_data['password1']
            )
            
            if user is not None:
                login(request, user)
                messages.success(request, 'Регистрация прошла успешно! Вы автоматически вошли в систему.')
                
                account_type = form.cleaned_data.get('account_type', 'individual')
                account_type_display = 'Физическое лицо' if account_type == 'individual' else 'Юридическое лицо'
                
                messages.info(request, f'Аккаунт создан как {account_type_display}')
                return redirect('profile')
            else:
                messages.error(request, 'Ошибка автоматического входа. Пожалуйста, войдите вручную.')
                return redirect('login')
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

from decimal import Decimal

@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.cartitem_set.all().select_related('product')
    
    addresses = Address.objects.filter(user=request.user).values(
        'id', 'title', 'full_name', 'phone', 'address', 
        'city', 'postal_code', 'is_default'
    )

    # Расчет НДС
    vat_total = Decimal('0')
    total_without_vat = Decimal('0')
    vat_rate = Decimal('20.00')
    
    for item in cart_items:
        item_total = item.get_total_price()
        item_vat = item_total * (vat_rate / 100) / (1 + vat_rate / 100)
        item_without_vat = item_total - item_vat
        
        vat_total += item_vat
        total_without_vat += item_without_vat
        
        item.vat_amount = item_vat
        item.price_without_vat = item_without_vat
        item.vat_rate = vat_rate
    
    subtotal = cart.get_total_price()
    
    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        
        if not address_id or address_id == '':
            messages.error(request, 'Выберите адрес доставки')
            return redirect('cart')
        
        try:
            address = Address.objects.get(id=address_id, user=request.user)
            
            # Создаем заказ только для оплаты по счету
            order = Order.objects.create(
                user=request.user,
                total_price=subtotal,
                final_price=subtotal,
                price_without_vat=total_without_vat,
                vat_amount=vat_total,
                payment_method='invoice',  # Только оплата по счету
                payment_fee=Decimal('0'),
                delivery_cost=Decimal('0'),
                vat_rate=vat_rate,
                customer_name=address.full_name,
                customer_phone=address.phone,
                customer_email=request.user.email,
                delivery_address=f"{address.city}, {address.address}, {address.postal_code}"
            )
            
            # Добавляем товары в заказ
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price,
                    vat_rate=vat_rate
                )
            
            # Очищаем корзину
            cart_items.delete()
            
            # Статус заказа
            order.status = 'processing'
            order.save()
            
            send_invoice_order_notification(order)
            
            messages.success(request, f'Заказ #{order.id} создан! Счет будет выставлен на вашу почту {request.user.email}.')
            return redirect('orders')
            
        except Address.DoesNotExist:
            messages.error(request, 'Выбранный адрес не найден')
            return redirect('cart')
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'addresses': list(addresses),
        'subtotal': subtotal,
        'final_price': subtotal,
        'vat_total': vat_total,
        'total_without_vat': total_without_vat,
        'vat_rate': vat_rate,
    }
    return render(request, 'main/cart.html', context)

def send_invoice_order_notification(order):
    """Отправка уведомления о создании заказа по счету"""
    try:
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            print("⚠️ TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не настроены")
            return False
    
        message = f"""
📄 <b>НОВЫЙ ЗАКАЗ ПО СЧЕТУ #{order.id}</b>

👤 <b>Клиент:</b> {order.customer_name}
📞 <b>Телефон:</b> {order.customer_phone}
📧 <b>Email:</b> {order.customer_email}
🚚 <b>Адрес доставки:</b> {order.delivery_address}

<b>Финансовые данные:</b>
💰 <b>Сумма товаров:</b> {order.total_price} руб.
📊 <b>Без НДС:</b> {order.total_without_vat} руб.
🏛️ <b>НДС:</b> {order.vat_amount} руб.

<b>Товары:</b>
"""
        
        for item in order.orderitem_set.all():
            message += f"• {item.product.name} x{item.quantity} - {item.get_total_price()} руб."
            if item.vat_rate:
                message += f" (НДС {item.vat_rate}% = {item.vat_amount} руб.)"
            message += "\n"
        
        message += f"\n<b>Итого:</b> {order.total_price} руб. (в т.ч. НДС {order.vat_amount} руб.)"
        message += f"\n\n💡 <b>Доставка не включена в счет</b>"
        message += f"\n⚡ <b>Требуется выставить счет на {order.total_price} руб.</b>"
        
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': settings.TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления: {e}")
        return False

@login_required
def update_cart_item(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        action = request.POST.get('action')
        
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Сохраняем старое количество для расчета НДС
        old_quantity = cart_item.quantity
        
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
        cart_items = cart.cartitem_set.all()
        cart_total = cart.get_total_price()
        item_count = cart.get_items_count()
        
        # Рассчитываем НДС
        vat_rate = Decimal('20.00')
        vat_total = Decimal('0')
        
        for item in cart_items:
            item_total = item.get_total_price()
            item_vat = item_total * (vat_rate / 100) / (1 + vat_rate / 100)
            vat_total += item_vat
        
        if is_ajax:
            return JsonResponse({
                'success': success,
                'message': message,
                'cart_total': float(cart_total),
                'item_count': item_count,
                'vat_total': float(vat_total),
                'vat_rate': float(vat_rate),
            })
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        
        return redirect('cart')
    
    return redirect('cart')

def rate_limit_payment(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            if RateLimiter.check_payment_rate_limit(request, request.user):
                return JsonResponse({
                    'success': False,
                    'error': 'Слишком много запросов. Попробуйте позже.'
                }, status=429)
        return view_func(request, *args, **kwargs)
    return wrapper


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
    """Обработка запроса на восстановление пароля"""
    if request.method == "POST":
        email = request.POST.get('email')
        
        if not email:
            return JsonResponse({
                'success': False,
                'error': 'Пожалуйста, введите email адрес'
            })
        
        # Проверяем валидность email
        if not is_valid_email(email):
            return JsonResponse({
                'success': False,
                'error': 'Пожалуйста, введите корректный email адрес'
            })

        if not check_rate_limit(email, 'password_reset', limit=1, timeout=300):
            return JsonResponse({
                'success': False,
                'error': 'Слишком много запросов. Попробуйте через 5 минут.'
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
            email_sent = send_password_reset_email_via_mail_ru(email, reset_code, user.username)
            
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

        commission_text = f"   • Комиссия: {order.payment_fee} руб.\n" if order.payment_fee else ""
    
        message = f"""
❌ <b>ЗАКАЗ ОТМЕНЕН #{order.id}</b>
        
👤 <b>Клиент:</b> {order.customer_name}
📞 <b>Телефон:</b> {order.customer_phone}
📧 <b>Email:</b> {order.customer_email}
💰 <b>Стоимость:</b>
   • Товары: {order.total_price} руб.
   • Доставка: {order.delivery_cost} руб.
{commission_text}   • <b>Итого: {order.final_price} руб.</b>
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
            
            # Отправляем подтверждение смены пароля
            send_password_changed_confirmation(user.email, user.username)
            
            return JsonResponse({
                'success': True,
                'message': 'Пароль успешно изменен! Теперь вы можете войти в систему.'
            })
            
        except UserProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Ссылка недействительна или устарела'
            })
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

def is_valid_email(email):
    """Проверка валидности email адреса"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

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
        
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.is_active = True
            user.save()
            
            profile, created = UserProfile.objects.get_or_create(user=user)
            login(request, user)
        
            log_security_event(user, 'register', ip_address, user_agent, True)
            
            messages.success(
                request, 
                'Регистрация успешна!'
            )
            return redirect('profile')
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

            if new_status == 'paid' and old_status != 'paid':
                order.finalize_payment()
            elif new_status != 'paid' and order.is_payment_finalized:
                order.is_payment_finalized = False
                order.save(update_fields=['is_payment_finalized'])
            
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
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            
            commission_text = f"   • Комиссия: {order.payment_fee} руб.\n" if order.payment_fee else ""

            message = f"""
🔄 <b>ИЗМЕНЕНИЕ СТАТУСА ЗАКАЗА #{order.id}</b>

📊 <b>Статус:</b> {dict(Order.STATUS_CHOICES)[old_status]} → {dict(Order.STATUS_CHOICES)[new_status]}
👤 <b>Клиент:</b> {order.customer_name}
📞 <b>Телефон:</b> {order.customer_phone}
💰 <b>Стоимость:</b>
   • Товары: {order.total_price} руб.
   • Доставка: {order.delivery_cost} руб.
{commission_text}   • <b>Итого: {order.final_price} руб.</b>

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
            commission_text = f"   • Комиссия: {order.payment_fee} руб.\n" if order.payment_fee else ""
            message = f"""
💰 <b>ЗАПРОС ВОЗВРАТА СРЕДСТВ</b>

🆔 <b>Заказ:</b> #{order.id}
👤 <b>Клиент:</b> {order.customer_name}
📞 <b>Телефон:</b> {order.customer_phone}
💰 <b>Стоимость:</b>
• Товары: {order.total_price} руб.
• Доставка: {order.delivery_cost} руб.
• Комиссия: {commission_text} руб.  

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

    product_images = product.get_images()
    
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
        'product_images': product_images,
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

def test_email_sending(request):
    """Тестовая функция для проверки отправки email"""
    try:
        send_mail(
            'Тест отправки email с локальной машины',
            'Поздравляю! Ваш Django успешно отправляет письма! 🎉',
            settings.DEFAULT_FROM_EMAIL,
            ['your_test_email@mail.ru'],  # ваш email для теста
            fail_silently=False,
        )
        return JsonResponse({'success': True, 'message': 'Email отправлен успешно!'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    

def support_view(request):
    if request.method == 'POST':
        form = SupportTicketForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                # Создаем заявку
                ticket = form.save(commit=False)
                
                # Добавляем информацию о пользователе
                if request.user.is_authenticated:
                    ticket.user = request.user
                
                # Добавляем техническую информацию
                ticket.ip_address = get_client_ip(request)
                ticket.user_agent = request.META.get('HTTP_USER_AGENT', '')
                
                ticket.save()
                
                # Обрабатываем файл
                attachment_file = request.FILES.get('attachments')
                if attachment_file:
                    try:
                        # Создаем запись вложения в базе данных
                        support_attachment = SupportAttachment(
                            ticket=ticket,
                            file=attachment_file,
                            file_name=attachment_file.name,  # Используем .name вместо .file_name
                            file_size=attachment_file.size
                        )
                        support_attachment.save()
                        
                    except Exception as e:
                        print(f"❌ Ошибка сохранения вложения {attachment_file.name}: {e}")
                
                # Отправляем уведомление в Telegram
                # Получаем все вложения для этой заявки
                ticket_attachments = SupportAttachment.objects.filter(ticket=ticket)
                send_support_notification(ticket, list(ticket_attachments))
                
                messages.success(request, '✅ Ваше обращение успешно отправлено! Мы свяжемся с вами в ближайшее время.')
                return redirect('support')
                
            except Exception as e:
                print(f"❌ Ошибка создания заявки: {e}")
                messages.error(request, '❌ Произошла ошибка при отправке обращения. Пожалуйста, попробуйте еще раз.')
        else:
            messages.error(request, '❌ Пожалуйста, исправьте ошибки в форме.')
    else:
        form = SupportTicketForm()
    
    context = {
        'form': form,
        'active_tab': 'support'
    }
    return render(request, 'main/support.html', context)

def send_simple_attachment(attachment, chat_id=None):
    """Упрощенная отправка вложения"""
    try:
        if chat_id is None:
            chat_id = settings.TELEGRAM_CHAT_ID_CONTACTS
            
        file_path = attachment.file.path
        
        # Всегда отправляем как документ
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"
        
        with open(file_path, 'rb') as file:
            files = {'document': file}
            data = {
                'chat_id': chat_id,
                'caption': f'Файл: {attachment.file_name}'
            }
            
            response = requests.post(url, data=data, files=files, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ Вложение {attachment.file_name} отправлено")
                return True
            else:
                print(f"❌ Ошибка отправки документа: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка отправки файла {attachment.file_name}: {e}")
        return False
    
def send_simple_attachment(attachment):
    """Упрощенная отправка вложения"""
    try:
        file_path = attachment.file.path
        
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"
        
        with open(file_path, 'rb') as file:
            files = {'document': file}
            data = {
                'chat_id': settings.TELEGRAM_CHAT_ID_CONTACTS,
                'caption': f'Файл: {attachment.file_name}'
            }
            
            response = requests.post(url, data=data, files=files, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ Вложение {attachment.file_name} отправлено")
                return True
            else:
                print(f"❌ Ошибка отправки документа: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка отправки файла {attachment.file_name}: {e}")
        return False

def check_bot_settings():
    """Проверка настроек бота"""
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            bot_info = response.json()
            print(f"✅ Бот настроен: {bot_info['result']['username']}")
            return True
        else:
            print(f"❌ Ошибка доступа к боту: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки бота: {e}")
        return False
    
def send_support_notification(ticket, attachments):
    """Отправка уведомления о новой заявке в поддержку в Telegram с полной технической информацией"""
    try:
        if ticket.priority == 'critical':
            chat_id = settings.TELEGRAM_CHAT_ID_CRITICAL
            priority_icon = "🚨🚨🚨"
            priority_text = "КРИТИЧЕСКИЙ ПРИОРИТЕТ"
        else:
            chat_id = settings.TELEGRAM_CHAT_ID_CONTACTS
            priority_icon = "🆘"
            priority_text = "НОВОЕ ОБРАЩЕНИЕ"
        
        if not settings.TELEGRAM_BOT_TOKEN or not chat_id:
            print(f"⚠️ TELEGRAM_BOT_TOKEN или chat_id не настроены")
            return False
        
        user_info = "Гость"
        user_email = "Не указан"
        user_id = "Не авторизован"
        
        if ticket.user:
            user_info = f"{ticket.user.username}"
            user_id = f"{ticket.user.id}"
            user_email = ticket.user.email if ticket.user.email else "Не указан"

        user_agent = ticket.user_agent or "Не указан"
        browser_info = parse_user_agent(user_agent)
        
        additional_info = get_additional_client_info(ticket)

        message = f"""
{priority_icon} {priority_text} #{ticket.id}

📋 Тема: {ticket.subject}
🚨 Приоритет: {ticket.get_priority_display()}
👤 Пользователь: {user_info}
🆔 User ID: {user_id}
📧 Email: {user_email}

📝 Описание:
{ticket.description}
"""
        
        # Отправка основного сообщения
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Ошибка отправки сообщения: {response.text}")
            return send_fallback_notification(ticket, attachments)
            
        # Отправка вложений если есть
        for attachment in attachments:
            try:
                send_attachment_with_quality(attachment, chat_id)
            except Exception as e:
                print(f"❌ Ошибка отправки вложения: {e}")
        
        # Логируем отправку
        NotificationLog.objects.create(
            notification_type='support_ticket',
            message=f'Заявка поддержки #{ticket.id} отправлена в Telegram ({ "CRITICAL" if ticket.priority == "critical" else "NORMAL" })',
            sent_to=f"Telegram: {chat_id}",
            success=True
        )
        
        print(f"✅ Уведомление о заявке #{ticket.id} отправлено в Telegram ({ 'КРИТИЧЕСКИЙ' if ticket.priority == 'critical' else 'ОБЫЧНЫЙ' })")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления поддержки: {e}")
        return send_fallback_notification(ticket, attachments)

def parse_user_agent(user_agent):
    """Парсинг User-Agent для получения информации о браузере и ОС"""
    try:
        # Простой парсинг User-Agent
        ua = user_agent.lower()
        browser_info = {}
        
        # Определяем браузер
        if 'chrome' in ua:
            browser_info['browser'] = 'Chrome'
        elif 'firefox' in ua:
            browser_info['browser'] = 'Firefox'
        elif 'safari' in ua:
            browser_info['browser'] = 'Safari'
        elif 'edge' in ua:
            browser_info['browser'] = 'Edge'
        elif 'opera' in ua:
            browser_info['browser'] = 'Opera'
        else:
            browser_info['browser'] = 'Неизвестный браузер'
        
        # Определяем ОС
        if 'windows' in ua:
            browser_info['os'] = 'Windows'
        elif 'mac' in ua:
            browser_info['os'] = 'macOS'
        elif 'linux' in ua:
            browser_info['os'] = 'Linux'
        elif 'android' in ua:
            browser_info['os'] = 'Android'
        elif 'iphone' in ua or 'ipad' in ua:
            browser_info['os'] = 'iOS'
        else:
            browser_info['os'] = 'Неизвестная ОС'
        
        # Определяем устройство
        if 'mobile' in ua:
            browser_info['device'] = 'Мобильное'
        elif 'tablet' in ua:
            browser_info['device'] = 'Планшет'
        else:
            browser_info['device'] = 'Десктоп'
            
        return browser_info
        
    except Exception as e:
        print(f"❌ Ошибка парсинга User-Agent: {e}")
        return {
            'browser': 'Ошибка парсинга',
            'os': 'Ошибка парсинга', 
            'device': 'Ошибка парсинга'
        }

def get_additional_client_info(ticket):
    """Получение дополнительной информации о клиенте"""
    try:
        
        info = {
            'request_method': 'POST',  
            'host': 'techresource.ru',  # Заменить на реальный домен
            'path': '/support/',
            'referer': 'Прямой заход',
            'cookies_enabled': 'Да (предположительно)',
            'javascript_enabled': 'Да (предположительно)',
            'screen_resolution': 'Неизвестно',
            'timezone': 'Неизвестно'
        }
        
        return info
        
    except Exception as e:
        print(f"❌ Ошибка получения доп. информации: {e}")
        return {}

def send_attachment_with_quality(attachment, chat_id):
    """Отправка вложения с сохранением качества фото"""
    try:
        file_path = attachment.file.path
        file_name = attachment.file_name.lower()
        
        # Определяем тип файла
        if any(ext in file_name for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            # Для изображений отправляем как документ для сохранения качества
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"
            
            with open(file_path, 'rb') as file:
                files = {'document': file}
                data = {
                    'chat_id': chat_id,
                    'caption': f'Зацените {attachment.file_name}'
                }
                
                response = requests.post(url, data=data, files=files, timeout=30)
        else:
            # Для остальных файлов используем стандартный подход
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"
            
            with open(file_path, 'rb') as file:
                files = {'document': file}
                data = {
                    'chat_id': chat_id,
                    'caption': f'📎 {attachment.file_name}'
                }
                
                response = requests.post(url, data=data, files=files, timeout=30)
        
        if response.status_code == 200:
            print(f"✅ Вложение {attachment.file_name} отправлено с сохранением качества")
            return True
        else:
            print(f"❌ Ошибка отправки вложения: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка отправки файла {attachment.file_name}: {e}")
        return False

def send_fallback_notification(ticket, attachments):
    """Резервный метод отправки уведомления"""
    try:
        # Определяем chat_id в зависимости от приоритета
        if ticket.priority == 'critical':
            chat_id = settings.TELEGRAM_CHAT_ID_CRITICAL
            prefix = "🚨🚨🚨 КРИТИЧЕСКАЯ ЗАЯВКА: "
        else:
            chat_id = settings.TELEGRAM_CHAT_ID_CONTACTS
            prefix = "🆘 Новая заявка поддержки: "
        
        # Простейшее уведомление без вложений
        message = f"{prefix}#{ticket.id}\nТема: {ticket.subject}\nПриоритет: {ticket.get_priority_display()}"
        
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Резервное уведомление отправлено для заявки #{ticket.id}")
            return True
        else:
            print(f"❌ Ошибка резервной отправки: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Критическая ошибка отправки: {e}")
        return False
    
def send_attachment_to_telegram(attachment):
    """Отправка вложения в Telegram"""
    try:
        file_path = attachment.file.path
        
        # Определяем тип файла для отправки
        file_extension = attachment.file_name.lower().split('.')[-1] if attachment.file_name else 'bin'
        
        if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
            # Отправка как фото
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendPhoto"
            files = {'photo': open(file_path, 'rb')}
            data = {
                'chat_id': settings.TELEGRAM_CHAT_ID_CONTACTS,
                'caption': f'📎 {attachment.file_name}'
            }
        elif file_extension in ['mp4', 'avi', 'mov', 'webm']:
            # Отправка как видео
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendVideo"
            files = {'video': open(file_path, 'rb')}
            data = {
                'chat_id': settings.TELEGRAM_CHAT_ID_CONTACTS,
                'caption': f'🎥 {attachment.file_name}'
            }
        else:
            # Отправка как документ по умолчанию
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"
            files = {'document': open(file_path, 'rb')}
            data = {
                'chat_id': settings.TELEGRAM_CHAT_ID_CONTACTS,
                'caption': f'📄 {attachment.file_name}'
            }
        
        response = requests.post(url, data=data, files=files, timeout=30)
        
        # Закрываем файл
        file_key = list(files.keys())[0]
        files[file_key].close()
        
        if response.status_code != 200:
            print(f"❌ Ошибка отправки вложения: {response.text}")
            return False
            
        print(f"✅ Вложение {attachment.file_name} отправлено в Telegram")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка отправки вложения: {e}")
        return False
    
class PaymentSecurityService:
    @staticmethod
    def verify_payment_amount(order, payment_data):
        """Проверка суммы платежа"""
        expected_amount = float(order.total_price)
        actual_amount = float(payment_data.get('amount', {}).get('value', 0))
        
        return abs(expected_amount - actual_amount) < 0.01

    @staticmethod
    def is_webhook_duplicate(payment_id, event_type):
        """Проверка на дублирование webhook"""
        cache_key = f"webhook_{payment_id}_{event_type}"
        if cache.get(cache_key):
            return True
        cache.set(cache_key, True, 86400)
        return False

    @staticmethod
    def create_webhook_signature(payload, secret):
        """Создание подписи для webhook"""
        return hmac.new(
            secret.encode(),
            json.dumps(payload, sort_keys=True).encode(),
            sha256
        ).hexdigest()
    
class RateLimiter:
    @staticmethod
    def is_rate_limited(key, limit, window):
        """Проверка лимита запросов"""
        cache_key = f"rate_limit_{key}"
        current = cache.get(cache_key, 0)
        
        if current >= limit:
            return True
        
        cache.set(cache_key, current + 1, window)
        return False

    @staticmethod
    def check_payment_rate_limit(request, user):
        """Проверка лимита для платежных операций"""
        user_key = f"payment_user_{user.id}"
        if RateLimiter.is_rate_limited(user_key, 10, 3600):
            return True
        
        ip_key = f"payment_ip_{get_client_ip(request)}"
        if RateLimiter.is_rate_limited(ip_key, 50, 3600):
            return True
        
        return False

def staff_required(function=None):
    """Декоратор для проверки staff статуса"""
    actual_decorator = user_passes_test(
        lambda u: u.is_active and u.is_staff,
        login_url='/admin/login/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

@staff_required
def admin_2fa_setup(request):
    """Настройка 2FA для администратора"""
    try:
        admin_2fa, created = Admin2FA.objects.get_or_create(user=request.user)
        
        backup_codes = None
        
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'generate':
                secret_key = admin_2fa.generate_secret_key()
                admin_2fa.generate_backup_codes()
                admin_2fa.save()
                
                messages.success(request, 'Секретный ключ сгенерирован! Настройте приложение аутентификации.')
                
            elif action == 'verify':
                code = request.POST.get('code', '').strip()
                
                if not code:
                    messages.error(request, 'Введите код подтверждения')
                else:
                    if admin_2fa.verify_totp(code, valid_window=1):
                        admin_2fa.is_enabled = True
                        admin_2fa.last_used = timezone.now()
                        admin_2fa.save()
                        
                        request.session['admin_2fa_verified'] = True
                        backup_codes = admin_2fa.backup_codes
                        
                        messages.success(request, '2FA успешно активирована! Сохраните резервные коды.')
                        return redirect('admin_2fa_setup')
                    else:
                        messages.error(request, 'Неверный код. Попробуйте снова.')
                        
            elif action == 'disable':
                admin_2fa.is_enabled = False
                admin_2fa.secret_key = ''
                admin_2fa.backup_codes = []
                admin_2fa.save()
                
                if 'admin_2fa_verified' in request.session:
                    del request.session['admin_2fa_verified']
                
                messages.success(request, '2FA отключена.')
                return redirect('admin_2fa_setup')
        
        context = {
            'admin_2fa': admin_2fa,
            'backup_codes': backup_codes or admin_2fa.backup_codes,
            'secret_key': admin_2fa.secret_key
        }
        
        return render(request, 'main/admin_2fa_setup.html', context)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, f'Ошибка настройки 2FA: {str(e)}')
        return render(request, 'main/admin_2fa_setup.html', {'error': str(e)})

@staff_required
def admin_2fa_verify(request):
    """Верификация 2FA для доступа в админку"""
    if request.session.get('admin_2fa_verified'):
        return redirect('admin:index')
    
    try:
        admin_2fa = Admin2FA.objects.get(user=request.user)
        
        if not admin_2fa.is_enabled:
            messages.info(request, 'Сначала настройте 2FA в панели администратора.')
            return redirect('admin_2fa_setup')
        
        if request.method == 'POST':
            code = request.POST.get('code', '').strip()
            use_backup = request.POST.get('use_backup', False)

            if not code:
                messages.error(request, 'Введите код подтверждения')
                return render(request, 'main/admin_2fa_verify.html')
            
            if use_backup:
                if admin_2fa.verify_backup_code(code):
                    request.session['admin_2fa_verified'] = True
                    admin_2fa.last_used = timezone.now()
                    admin_2fa.save()
                    messages.success(request, 'Вход выполнен с использованием резервного кода.')
                    return redirect('admin:index')
                else:
                    messages.error(request, 'Неверный резервный код.')
            else:
                if admin_2fa.verify_totp(code, valid_window=1):
                    request.session['admin_2fa_verified'] = True
                    admin_2fa.last_used = timezone.now()
                    admin_2fa.save()
                    messages.success(request, '2FA проверка пройдена!')
                    return redirect('admin:index')
                else:
                    messages.error(request, 'Неверный код. Попробуйте снова.')
        
        return render(request, 'main/admin_2fa_verify.html')
        
    except Admin2FA.DoesNotExist:
        Admin2FA.objects.create(user=request.user)
        messages.info(request, 'Сначала настройте 2FA.')
        return redirect('admin_2fa_setup')
    except Exception as e:
        messages.error(request, f'Ошибка верификации: {str(e)}')
        return render(request, 'main/admin_2fa_verify.html')

@login_required
# Статические страницы услуг (оставляем как есть)
def service_design(request):
    """Страница услуги - Проектирование систем"""
    navigation_tree = ServicePage.get_navigation_tree()  # Для навигации
    return render(request, 'main/service_design.html', {
        'navigation_tree': navigation_tree
    })

def service_electrical(request):
    """Страница услуги - Электромонтажные работы"""
    navigation_tree = ServicePage.get_navigation_tree()
    return render(request, 'main/service_electrical.html', {
        'navigation_tree': navigation_tree
    })

def service_software(request):
    """Страница услуги - Разработка ПО и SCADA"""
    navigation_tree = ServicePage.get_navigation_tree()
    return render(request, 'main/service_software.html', {
        'navigation_tree': navigation_tree
    })

def service_equipment(request):
    """Страница услуги - Поставка оборудования"""
    navigation_tree = ServicePage.get_navigation_tree()
    return render(request, 'main/service_equipment.html', {
        'navigation_tree': navigation_tree
    })

def service_support(request):
    """Страница услуги - Техническая поддержка"""
    navigation_tree = ServicePage.get_navigation_tree()
    return render(request, 'main/service_support.html', {
        'navigation_tree': navigation_tree
    })

def service_maintenance(request):
    """Страница услуги - Сервисное обслуживание"""
    navigation_tree = ServicePage.get_navigation_tree()
    return render(request, 'main/service_maintenance.html', {
        'navigation_tree': navigation_tree
    })

def services_main(request):
    """Главная страница услуг"""
    navigation_tree = ServicePage.get_navigation_tree()
    
    context = {
        'navigation_tree': navigation_tree,
    }
    return render(request, 'main/services.html', context)

def dynamic_service_page(request, service_slug, sub_slug=None, instruction_slug=None):
    """Универсальное представление для ДОПОЛНИТЕЛЬНЫХ динамических страниц"""
    try:
        if instruction_slug and sub_slug:
            # Страница инструкции: /services/{service_slug}/{sub_slug}/instructions/{instruction_slug}/
            page = ServicePage.objects.get(
                slug=instruction_slug,
                page_type='instruction',
                parent__slug=sub_slug,
                parent__parent__slug=service_slug,
                is_active=True
            )
        elif sub_slug:
            # Страница подуслуги: /services/{service_slug}/{sub_slug}/
            page = ServicePage.objects.get(
                slug=sub_slug,
                page_type='sub_service', 
                parent__slug=service_slug,
                is_active=True
            )
        else:
            # Основная услуга: /services/{service_slug}/
            page = ServicePage.objects.get(
                slug=service_slug,
                page_type='main_service',
                is_active=True
            )
        
    except ServicePage.DoesNotExist:
        # Если страница не найдена, показываем 404
        raise Http404("Страница не найдена")
    
    navigation_tree = ServicePage.get_navigation_tree()
    breadcrumbs = page.get_breadcrumbs()
    
    context = {
        'page': page,
        'navigation_tree': navigation_tree,
        'breadcrumbs': breadcrumbs,
    }
    
    return render(request, 'main/dynamic_service_page.html', context)

def send_password_reset_email_via_mail_ru(email, code, username):
    """Отправка email с кодом восстановления через Mail.ru"""
    try:
        subject = "Код восстановления пароля - Техресурс"
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    color: #333;
                    line-height: 1.6;
                    margin: 0;
                    padding: 0;
                    background-color: #f8f9fa;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: white;
                    border-radius: 10px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #0052cc 0%, #0066cc 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                    font-weight: bold;
                }}
                .content {{
                    padding: 30px;
                }}
                .code-box {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    font-size: 32px;
                    font-weight: bold;
                    text-align: center;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 30px 0;
                    letter-spacing: 5px;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e9ecef;
                    color: #6c757d;
                    font-size: 12px;
                    text-align: center;
                }}
                .security-note {{
                    background-color: #fff5f5;
                    border: 1px solid #fed7d7;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 20px 0;
                    color: #742a2a;
                }}
                @media (max-width: 600px) {{
                    .container {{
                        padding: 10px;
                    }}
                    .header {{
                        padding: 20px;
                    }}
                    .content {{
                        padding: 20px;
                    }}
                    .code-box {{
                        font-size: 24px;
                        padding: 15px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Техресурс</h1>
                    <p>Восстановление пароля</p>
                </div>
                
                <div class="content">
                    <h2>Здравствуйте, {username}!</h2>
                    <p>Вы запросили восстановление пароля для вашего аккаунта на сайте Техресурс.</p>
                    <p>Используйте следующий код для подтверждения:</p>
                    
                    <div class="code-box">
                        {code}
                    </div>
                    
                    <div class="security-note">
                        <strong>Важная информация:</strong>
                        <p>• Код действителен в течение 10 минут</p>
                        <p>• Не передавайте код третьим лицам</p>
                        <p>• Если вы не запрашивали восстановление пароля, проигнорируйте это письмо</p>
                    </div>
                    
                    <p>Если у вас возникли проблемы с вводом кода, попробуйте:</p>
                    <ul>
                        <li>Скопировать код и вставить в поле ввода</li>
                        <li>Проверить, нет ли лишних пробелов</li>
                        <li>Запросить новый код, если этот истек</li>
                    </ul>
                    
                    <p>С уважением,<br>Команда Техресурс</p>
                </div>
                
                <div class="footer">
                    <p>Это письмо отправлено автоматически. Пожалуйста, не отвечайте на него.</p>
                    <p>© {timezone.now().year} Техресурс. Все права защищены.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Текстовая версия письма
        plain_message = f"""
        Восстановление пароля - Техресурс
        
        Здравствуйте, {username}!
        
        Вы запросили восстановление пароля для вашего аккаунта на сайте Техресурс.
        
        Ваш код восстановления:
        
        {code}
        
        Введите этот код на странице восстановления пароля.
        
        Код действителен в течение 10 минут.
        
        Важная информация:
        • Не передавайте код третьим лицам
        • Если вы не запрашивали восстановление пароля, проигнорируйте это письмо
        
        Если у вас возникли проблемы с вводом кода:
        • Скопируйте код и вставьте в поле ввода
        • Проверьте, нет ли лишних пробелов
        • Запросите новый код, если этот истек
        
        С уважением,
        Команда Техресурс
        
        Это письмо отправлено автоматически. Пожалуйста, не отвечайте на него.
        © {timezone.now().year} Техресурс. Все права защищены.
        """
        
        # Отправка email через Django
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        
        print(f"✅ Email с кодом отправлен на {email}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка отправки email на {email}: {str(e)}")
        return False

def send_password_changed_confirmation(email, username):
    """Отправка подтверждения смены пароля"""
    try:
        subject = "Пароль успешно изменен - Техресурс"
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .success-icon {{ font-size: 48px; text-align: center; margin: 20px 0; color: #48bb78; }}
                .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Техресурс</h1>
                    <p>Пароль успешно изменен</p>
                </div>
                <div class="content">
                    <div class="success-icon">✅</div>
                    <h2>Здравствуйте, {username}!</h2>
                    <p>Мы подтверждаем, что пароль для вашего аккаунта был успешно изменен.</p>
                    <p><strong>Дата изменения:</strong> {timezone.now().strftime('%d.%m.%Y %H:%M')}</p>
                    
                    <div style="background: #fff5f5; border: 1px solid #fed7d7; border-radius: 8px; padding: 15px; margin: 20px 0;">
                        <strong>⚠️ Важная информация о безопасности:</strong>
                        <p>Если вы не изменяли пароль, немедленно свяжитесь с нашей поддержкой.</p>
                    </div>
                    
                    <p>Теперь вы можете войти в систему с новым паролем.</p>
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
        Пароль успешно изменен - Техресурс
        
        Здравствуйте, {username}!
        
        Мы подтверждаем, что пароль для вашего аккаунта был успешно изменен.
        
        Дата изменения: {timezone.now().strftime('%d.%m.%Y %H:%M')}
        
        Важная информация о безопасности:
        Если вы не изменяли пароль, немедленно свяжитесь с нашей поддержкой.
        
        Теперь вы можете войти в систему с новым паролем.
        
        С уважением,
        Команда Техресурс
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        
        print(f"✅ Подтверждение смены пароля отправлено на {email}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка отправки подтверждения: {e}")
        return False

def check_rate_limit(email, action, limit=3, timeout=300):
    """Проверка частоты запросов с указанием действия"""
    key = f"rate_limit_{action}_{email}"
    attempts = cache.get(key, 0)
    
    if attempts >= limit:
        return False
    
    cache.set(key, attempts + 1, timeout)
    return True