# main/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.utils.html import strip_tags
from django.contrib.admin.views.decorators import staff_member_required
import json
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Min, Max
import secrets
from django.views.decorators.csrf import ensure_csrf_cookie
from decimal import Decimal
import requests
from .models import NotificationLog
import uuid
import io
from io import BytesIO
from django.contrib.auth.decorators import user_passes_test
import logging
from django.core.cache import cache
from hashlib import sha256
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import random
from datetime import timedelta
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
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
from django.core.files.storage import default_storage
from weasyprint import HTML, CSS
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import SupportAttachment
from .forms import SupportTicketForm
import tempfile
from blog.models import BlogComment, BlogArticle
from .models import Product, Cart, CartItem, Order, OrderItem, UserProfile, Address, NotificationLog, SecurityLog, PasswordResetToken, LoginAttempt, OrderStatusLog, WishlistItem, Wishlist, ProductReview, Admin2FA, ServicePage, InvoiceRegistry, Category, CurrencyRate
from .forms import SecureUserCreationForm, SecureAuthenticationForm, SecurePasswordResetForm, SecureSetPasswordForm, UserRegisterForm, UserProfileForm, AddressForm, ProductReviewForm, AdminProfileTagsForm, SupportTicketForm
from django.db.models import Sum
import qrcode
import qrcode.image.svg
import base64
from django.urls import reverse
from PIL import Image
import csv
import xlsxwriter


User = get_user_model()

logger = logging.getLogger(__name__)

def index(request):
    featured_products = Product.objects.filter(is_active=True, quantity__gt=0)[:6]
    
    for product in featured_products:
        product.price_in_rub = product.get_display_price('RUB')
    
    return render(request, 'main/index.html', {'featured_products': featured_products})

def about(request):
    return render(request, 'main/about.html')

def yandex_8820f023c5e740e9(request):
    return render(request, 'main/yandex_8820f023c5e740e9.html')
    
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
    
    orders = Order.objects.all().order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    date_filter = request.GET.get('date')
    if date_filter:
        orders = orders.filter(created_at__date=date_filter)
    
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    paid_orders = Order.objects.filter(is_payment_finalized=True).count()
    
    total_revenue = Order.objects.filter(status='paid').aggregate(
        total=Sum('final_price')
    )['total'] or 0

    total_gross = Order.objects.filter(is_payment_finalized=True).aggregate(
        total=Sum('paid_amount')
    )['total'] or 0

    pending_reviews = ProductReview.objects.filter(
        is_moderated=False
    ).select_related('user', 'product').order_by('-created_at')
    
    pending_reviews_count = pending_reviews.count()

    pending_comments = BlogComment.objects.filter(
        status='pending'
    ).select_related('user', 'article').order_by('-created_at')
    
    pending_comments_count = pending_comments.count()
    
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
        'pending_comments': pending_comments,
        'pending_comments_count': pending_comments_count,
    }
    
    return render(request, 'main/admin_dashboard.html', context)

@staff_member_required
def moderate_comment(request, comment_id):
    """Модерация комментария блога"""
    comment = get_object_or_404(BlogComment, id=comment_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approved': 
            comment.status = 'approved'
            comment.moderated_by = request.user
            comment.moderated_at = timezone.now()
            comment.save()
            
            ip_address = get_client_ip(request)

            SecurityLog.objects.create(
                user=request.user,
                action='comment_moderated',
                ip_address=ip_address,
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={
                    'comment_id': comment.id,
                    'article_id': comment.article.id,
                    'action': 'approved',
                    'user_id': comment.user.id if comment.user else None,
                },
                success=True,
                risk_level='low'
            )
            
            messages.success(request, f'Комментарий #{comment.id} одобрен')
            
        elif action == 'rejected':  
            comment.status = 'rejected'
            comment.moderated_by = request.user
            comment.moderated_at = timezone.now()
            comment.save()
            
            ip_address = get_client_ip(request)

            SecurityLog.objects.create(
                user=request.user,
                action='comment_moderated',
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={
                    'comment_id': comment.id,
                    'article_id': comment.article.id,
                    'action': 'rejected',
                    'user_id': comment.user.id if comment.user else None,
                },
                success=True,
                risk_level='low'
            )
            
            messages.success(request, f'Комментарий #{comment.id} отклонен')
        
        elif action == 'spam': 
            comment.status = 'spam'
            comment.moderated_by = request.user
            comment.moderated_at = timezone.now()
            comment.save()

            ip_address = get_client_ip(request)
            
            SecurityLog.objects.create(
                user=request.user,
                action='comment_moderated',
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={
                    'comment_id': comment.id,
                    'article_id': comment.article.id,
                    'action': 'marked_as_spam',
                    'user_id': comment.user.id if comment.user else None,
                },
                success=True,
                risk_level='medium'
            )
            
            messages.warning(request, f'Комментарий #{comment.id} помечен как спам')
        
        else:
            messages.error(request, f'Неизвестное действие: {action}')
    
    return redirect('admin_dashboard')

@staff_member_required
def moderate_all_comments(request):
    """Массовая модерация комментариев"""
    if request.method != 'POST':
        messages.error(request, 'Неверный метод запроса')
        return redirect('admin_dashboard')
    
    action = request.POST.get('action')
    comment_ids = request.POST.getlist('comment_ids')
    
    if not comment_ids:
        messages.error(request, 'Не выбраны комментарии для модерации')
        return redirect('admin_dashboard')
    
    if not action:
        messages.error(request, 'Не указано действие')
        return redirect('admin_dashboard')
    
    comments = BlogComment.objects.filter(id__in=comment_ids)
    updated = 0
    
    if action == 'approve_all':
        updated = comments.update(status='approved')
        messages.success(request, f'{updated} комментариев одобрено')
        
    elif action == 'reject_all':
        updated = comments.update(status='deleted')
        messages.success(request, f'{updated} комментариев отклонено (помечено как удаленные)')
        
    elif action == 'spam_all':
        updated = comments.update(status='spam')
        messages.warning(request, f'{updated} комментариев помечено как спам')
    
    elif action == 'pending_all':
        updated = comments.update(status='pending')
        messages.info(request, f'{updated} комментариев возвращено на модерацию')
    
    else:
        messages.error(request, f'Неизвестное действие: {action}')
        return redirect('admin_dashboard')
    
    # Логирование
    try:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        SecurityLog.objects.create(
            user=request.user,
            action='bulk_comment_moderation',
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                'action': action,
                'count': updated,
                'comment_ids': comment_ids,
            },
            success=True,
            risk_level='low'
        )
    except Exception as e:
        pass
    
    return redirect('admin_dashboard')

@staff_member_required
def moderate_review(request, review_id):
    """Модерация отзыва"""
    review = get_object_or_404(ProductReview, id=review_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approvedd':
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
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    brand_filter = request.GET.get('brand', '')
    price_min = request.GET.get('price_min', '')
    price_max = request.GET.get('price_max', '')
    in_stock = request.GET.get('in_stock', '')
    sort_by = request.GET.get('sort_by', 'name')
    display_currency = request.GET.get('currency', 'RUB')
    currency_symbols = {
        'RUB': '₽',
        'USD': '$',
        'EUR': '€',
    }
    products_list = Product.objects.filter(is_active=True).select_related('category')
    
    if search_query:
        products_list = products_list.filter(
            Q(name__icontains=search_query) |
            Q(article__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(material__icontains=search_query)
        )
    
    if category_filter:
        try:
            category = Category.objects.get(slug=category_filter, is_active=True)
            selected_category = category
            
            def get_all_children_ids(category_obj, result=None):
                if result is None:
                    result = []
                result.append(category_obj.id)
                for child in category_obj.children.filter(is_active=True):
                    get_all_children_ids(child, result)
                return result
            
            category_ids = get_all_children_ids(category)
            
            products_list = products_list.filter(category_id__in=category_ids)
            
        except Category.DoesNotExist:
            selected_category = None
    else:
        selected_category = None

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
    
    paginator = Paginator(products_list, 12)  
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    categories = Category.objects.filter(
        parent__isnull=True,  
        is_active=True
    ).prefetch_related('children').order_by('order', 'name')
    
    def build_category_tree(category_list):
        result = []
        for cat in category_list:
            result.append({
                'id': cat.id,
                'name': cat.name,
                'slug': cat.slug,
                'product_count': cat.product_count,
                'children': build_category_tree(cat.children.filter(is_active=True).order_by('order', 'name'))
            })
        return result

    category_tree = build_category_tree(categories)
    brands = Product.objects.filter(is_active=True).values_list('brand', flat=True).distinct()
    
    price_range = products_list.aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )
    
    if request.user.is_authenticated:
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            wishlist_product_ids = wishlist.wishlistitem_set.values_list('product_id', flat=True)
            
            for product in page_obj:
                product.in_wishlist = product.id in wishlist_product_ids
                product.average_rating = ProductReview.get_average_rating(product)
                product.reviews_count = ProductReview.get_approved_reviews(product).count()
                product.display_price_value = product.get_display_price(display_currency)
                product.display_currency = display_currency
                currency_symbols = {
                    'RUB': '₽',
                    'USD': '$',
                    'EUR': '€',
                }
                product.currency_symbol = currency_symbols.get(display_currency, '₽')
        except Wishlist.DoesNotExist:
            for product in page_obj:
                product.in_wishlist = False
                product.display_price_value = product.get_display_price(display_currency)
                product.currency_symbol = currency_symbols.get(display_currency, '₽')
    else:
        for product in page_obj:
            product.in_wishlist = False
            product.display_price_value = product.get_display_price(display_currency)
            product.currency_symbol = currency_symbols.get(display_currency, '₽')
    
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
        'display_currency': display_currency,
        'available_currencies': [
            ('RUB', '₽ Рубли'),
            ('USD', '$ Доллары'),
            ('EUR', '€ Евро'),
        ],
        'products': page_obj,
        'page_obj': page_obj,
        'category_tree': category_tree,
        'selected_category': selected_category,
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
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.template.loader import render_to_string
        
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
    
    prices_in_rub = []
    for product in products:
        price_in_rub = product.get_display_price('RUB')
        prices_in_rub.append(float(price_in_rub))
    
    if prices_in_rub:
        min_price = min(prices_in_rub)
        max_price = max(prices_in_rub)
    else:
        min_price = 0
        max_price = 10000
    
    return JsonResponse({
        'min_price': min_price,
        'max_price': max_price
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
    
    if user_profile.profile_background and not user_profile.has_background():
        user_profile.profile_background = None
        user_profile.save(update_fields=['profile_background'])
        messages.info(request, 'Недействительный фон профиля был удален')
    
    addresses = Address.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    profile_form = UserProfileForm(instance=user_profile)
    public_profile_form = UserProfileForm(instance=user_profile)
    address_form = AddressForm()
    
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, instance=user_profile)
            if profile_form.is_valid():
                try:
                    profile_form.save()
                    messages.success(request, 'Профиль обновлен')
                    return redirect('profile')
                except Exception as e:
                    messages.error(request, f'Ошибка при сохранении: {str(e)}')
        
        elif 'update_public_profile' in request.POST:
            public_profile_form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
            if public_profile_form.is_valid():
                try:
                    if 'profile_background' in request.FILES:
                        background_file = request.FILES['profile_background']
                        if background_file.size > 10 * 1024 * 1024:  
                            messages.error(request, 'Файл фона слишком большой (макс. 10MB)')
                        else:
                            public_profile_form.save()
                            messages.success(request, 'Настройки публичного профиля обновлены')
                            return redirect('profile')
                    else:
                        public_profile_form.save()
                        messages.success(request, 'Настройки публичного профиля обновлены')
                        return redirect('profile')
                except Exception as e:
                    messages.error(request, f'Ошибка при сохранении фона: {str(e)}')
                
        elif 'add_address' in request.POST:
            address_form = AddressForm(request.POST)
            if address_form.is_valid():
                address = address_form.save(commit=False)
                address.user = request.user
                address.save()
                messages.success(request, 'Адрес добавлен')
                return redirect('profile')
    
    context = {
        'user_profile': user_profile,  
        'profile_form': profile_form,
        'public_profile_form': public_profile_form,
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

    vat_total = Decimal('0')
    total_without_vat = Decimal('0')
    vat_rate = Decimal('22.00')
    
    for item in cart_items:
        item_total = item.get_total_price() 
        item_vat = item_total * (vat_rate / 100) / (1 + vat_rate / 100)
        item_without_vat = item_total - item_vat
        
        vat_total += item_vat
        total_without_vat += item_without_vat
        
        item.vat_amount = item_vat
        item.price_without_vat = item_without_vat
        item.vat_rate = vat_rate
        item.unit_price_in_rub = item.get_unit_price_in_rub()
    
    subtotal = cart.get_total_price()
    
    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        
        if not address_id or address_id == '':
            messages.error(request, 'Выберите адрес доставки')
            return redirect('cart')
        
        try:
            address = Address.objects.get(id=address_id, user=request.user)

            customer_inn = request.POST.get('customer_inn', '')
            customer_kpp = request.POST.get('customer_kpp', '')

            for cart_item_check in cart_items:
                if cart_item_check.product.quantity < cart_item_check.quantity:
                    messages.error(request, f'Недостаточно товара "{cart_item_check.product.name}" на складе. Доступно: {cart_item_check.product.quantity}')
                    return redirect('cart')
            
            order = Order.objects.create(
                user=request.user,
                total_price=subtotal,
                final_price=subtotal,
                price_without_vat=total_without_vat,
                vat_amount=vat_total,
                payment_method='invoice',
                payment_fee=Decimal('0'),
                delivery_cost=Decimal('0'),
                vat_rate=vat_rate,
                customer_name=address.full_name,
                customer_phone=address.phone,
                customer_email=request.user.email,
                delivery_address=f"{address.city}, {address.address}, {address.postal_code}",
                customer_inn=customer_inn,
                customer_kpp=customer_kpp,
                invoice_date=timezone.now().date(), 
            )

            order.invoice_number = order.generate_invoice_number()
            order.save(update_fields=['invoice_number'])
            
            for cart_item_order in cart_items:
                price_in_rub = cart_item_order.get_unit_price_in_rub()
                OrderItem.objects.create(
                    order=order,
                    product=cart_item_order.product,
                    quantity=cart_item_order.quantity,
                    price=price_in_rub, 
                    vat_rate=vat_rate
                )

                cart_item_order.product.quantity -= cart_item_order.quantity
                cart_item_order.product.save()
            cart_items.delete()
            order.status = 'processing'
            order.save()
            
            send_invoice_email(order)
            
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

@login_required
def update_cart_item(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        action = request.POST.get('action')
        
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
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

        cart = Cart.objects.get(user=request.user)
        cart_items = cart.cartitem_set.all()
        cart_total = cart.get_total_price()
        item_count = cart.get_items_count()
        
        vat_rate = Decimal('22.00')
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
def resend_invoice(request, order_id):
    """Повторная отправка счета"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method == 'POST':
        try:
            success = send_invoice_email(order)
            
            if success:
                messages.success(request, f'Счет №{order.invoice_number} повторно отправлен на {order.customer_email}')
            else:
                messages.error(request, 'Ошибка отправки счета')
                
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    
    return redirect('orders')

@login_required
@require_http_methods(["POST"])
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    try:
        if order.can_be_cancelled():
            old_status = order.status
            order.status = 'cancelled'
            order.cancelled_at = timezone.now()
            order.save()
            
            for item in order.orderitem_set.all():
                item.product.quantity += item.quantity
                item.product.save()
            
            OrderStatusLog.objects.create(
                order=order,
                old_status=old_status,
                new_status='cancelled',
                changed_by=request.user,
                notes="Отменен пользователем через сайт"
            )
            
            send_cancellation_notification(order)
            
            NotificationLog.objects.create(
                order=order,
                notification_type='order_cancelled',
                message=f'Заказ #{order.id} отменен пользователем',
                sent_to=f"Telegram: {settings.TELEGRAM_CHAT_ID}",
                success=True
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Заказ #{order.id} отменен.'
            })
                
        else:
            now = timezone.now()
            if order.paid_at:
                time_since_payment = (now - order.paid_at).total_seconds()
                time_left = max(0, 600 - time_since_payment) 
            else:
                time_since_creation = (now - order.created_at).total_seconds()
                time_left = max(0, 600 - time_since_creation)
            
            if time_left > 0:
                minutes_left = int(time_left // 60)
                seconds_left = int(time_left % 60)
                time_message = f"{minutes_left} мин {seconds_left} сек"
            else:
                time_message = "время истекло"
            
            return JsonResponse({
                'success': False,
                'error': f'Невозможно отменить заказ. Отмена доступна только в течение 5 минут после создания/оплаты. ({time_message})'
            })
                
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при отмене заказа: {str(e)}'
        })

@login_required
def orders_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'main/orders.html', {'orders': orders})
    
def password_reset_request(request):
    """Обработка запроса на восстановление пароля"""
    if request.method == "POST":
        email = request.POST.get('email')
        
        if not email:
            return JsonResponse({
                'success': False,
                'error': 'Пожалуйста, введите email адрес'
            })
        
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
        
        try:
            user = User.objects.get(email=email)
            
            reset_code = str(random.randint(100000, 999999))
            
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.sms_code = reset_code
            profile.sms_code_expires = timezone.now() + timedelta(minutes=10)
            profile.save()
            
            email_sent = send_password_reset_email_via_mail_ru(email, reset_code, user.username)
            
            if email_sent:
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
            return JsonResponse({
                'success': True,
                'message': 'Если email зарегистрирован, код будет отправлен'
            })
        except Exception as e:
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
        return False

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
            
            user = profile.user
            user.set_password(new_password)
            user.save()
            
            profile.reset_token = None
            profile.reset_token_expires = None
            profile.save()
            
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
            
            if (profile.sms_code == code and 
                profile.sms_code_expires and 
                profile.sms_code_expires > timezone.now()):
                
                reset_token = str(uuid.uuid4())
                profile.sms_code = None
                profile.sms_code_expires = None
                profile.reset_token = reset_token
                profile.reset_token_expires = timezone.now() + timedelta(hours=1)
                profile.save()
                
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
        ip = get_client_ip(request)
    if not ip or ip == '':
        ip = get_client_ip(request)
    
    return ip

def log_security_event(user, action, ip_address, user_agent, success=True):
    if ip_address is None:
        ip_address = None

    SecurityLog.objects.create(
        user=user,
        action=action,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success
    )

def get_client_ip(request):
    """
    Получение IP-адреса клиента.
    Возвращает IP или None, если адрес не определен.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    if ip and ip != '' and ip != 'unknown':
        if '.' in ip or ':' in ip: 
            return ip
    
    return None

@csrf_protect
@require_http_methods(["GET", "POST"])
def secure_register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        
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
                attempt = LoginAttempt.objects.filter(
                    username=username, 
                    ip_address=ip_address
                ).last()
                if attempt:
                    attempt.success = True
                    attempt.save()
                
                log_security_event(user, 'login', ip_address, user_agent, True)
                
                if 'login_attempts' in request.session:
                    del request.session['login_attempts']
                
                messages.success(request, 'Вход выполнен успешно!')
                return redirect('profile')
        
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
                
                token = secrets.token_urlsafe(32)
                expires_at = timezone.now() + timedelta(hours=1)
                
                PasswordResetToken.objects.create(
                    user=user,
                    token=token,
                    expires_at=expires_at,
                    ip_address=ip_address
                )
                
                send_password_reset_email(user, token, request)
                
                log_security_event(user, 'password_reset_request', ip_address, user_agent, True)
                
            except User.DoesNotExist:
                pass
            
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
            user = reset_token.user
            user.set_password(form.cleaned_data['password1'])
            user.save()
            
            reset_token.used = True
            reset_token.save()
            log_security_event(user, 'password_reset_success', ip_address, user_agent, True)
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
            current_password = request.POST.get('current_password')
            if not request.user.check_password(current_password):
                messages.error(request, 'Текущий пароль неверен.')
                log_security_event(request.user, 'password_change_failed', ip_address, user_agent, False)
            else:
                request.user.set_password(form.cleaned_data['password1'])
                request.user.save()
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, request.user)
                log_security_event(request.user, 'password_change', ip_address, user_agent, True)
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
            
            ip_address = get_client_ip(request)
            
            success = send_contact_message(name, email, phone, message, ip_address)
            
            if success:
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
            return JsonResponse({
                'success': False,
                'error': 'Произошла ошибка. Попробуйте еще раз.'
            })
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@staff_member_required
def update_order_status(request, order_id=None):
    """Обновление статуса заказа (для админов)"""
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
                if order.status != 'paid':  
                    for item in order.orderitem_set.all():
                        if item.product.quantity >= item.quantity:
                            item.product.quantity -= item.quantity
                            item.product.save()
                        else:
                            messages.warning(request, f'Недостаточно товара "{item.product.name}" на складе. Требуется пополнение.')
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
            
            order.status = new_status
            order.status_changed_at = timezone.now()
            
            if tracking_number:
                order.tracking_number = tracking_number
            if shipping_company:
                order.shipping_company = shipping_company
            if estimated_delivery:
                try:
                    from datetime import datetime
                    order.estimated_delivery = datetime.strptime(estimated_delivery, '%Y-%m-%d').date()
                except ValueError:
                    pass
                
            order.save()
            
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
        return False

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
        return False


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
        return False

@login_required
def request_order_refund(request, order_id):
    """Запрос на возврат средств"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        if order.status in ['paid', 'completed']:
            order.status = 'refunded'
            order.save()
            
            OrderStatusLog.objects.create(
                order=order,
                old_status=order.status,
                new_status='refunded',
                notes=f"Запрос возврата: {reason}"
            )
            
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
            
            wishlist_item = WishlistItem.objects.filter(
                wishlist=wishlist, 
                product=product
            ).first()
            
            if wishlist_item:
                wishlist_item.delete()
                action = 'removed'
                message = 'Товар удален из избранного'
            else:
                WishlistItem.objects.create(wishlist=wishlist, product=product)
                action = 'added'
                message = 'Товар добавлен в избранное'
            
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
            WishlistItem.objects.filter(wishlist=wishlist, product=product).delete()
            cart, created = Cart.objects.get_or_create(user=request.user)
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            
            if not created:
                cart_item.quantity += 1
                cart_item.save()
    
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

@login_required
def add_review(request, product_id):
    """Добавление отзыва к товару"""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
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

def product_detail(request, product_id):
    """Детальная страница товара"""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    product.display_price_value = product.get_display_price('RUB') 
    if hasattr(product, 'currency'):
        product.original_price = product.price
        product.original_currency = product.currency
    currency_symbols = {
        'RUB': '₽',
        'USD': '$',
        'EUR': '€',
    }
    product.currency_symbol = currency_symbols.get('RUB', '₽') 
    product_images = product.get_images()
    
    similar_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id)[:4]
    
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
    
    reviews_list = ProductReview.get_approved_reviews(product)
    paginator = Paginator(reviews_list, 5) 
    page = request.GET.get('page')
    
    try:
        reviews = paginator.page(page)
    except PageNotAnInteger:
        reviews = paginator.page(1)
    except EmptyPage:
        reviews = paginator.page(paginator.num_pages)
    
    average_rating = ProductReview.get_average_rating(product)
    
    can_review = False
    user_review = None
    if request.user.is_authenticated:
        can_review = ProductReview.can_user_review(request.user, product)
        user_review = ProductReview.objects.filter(
            user=request.user, 
            product=product
        ).first()
    
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
@require_http_methods(["POST"])
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
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при повторении заказа: {str(e)}'
        })

@login_required
def order_details(request, order_id):
    """Детальная информация о заказе"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    status_logs = OrderStatusLog.objects.filter(order=order).order_by('-changed_at')
    
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

def support_view(request):
    if request.method == 'POST':
        form = SupportTicketForm(request.POST, request.FILES)
        if not form.is_valid():
            print("DEBUG: Ошибки формы:", form.errors.as_json())
            
        if form.is_valid():
            try:
                ticket = form.save(commit=False)
                
                if request.user.is_authenticated:
                    ticket.user = request.user
                
                ticket.ip_address = get_client_ip(request)
                ticket.user_agent = request.META.get('HTTP_USER_AGENT', '')
                
                ticket.save()
                
                attachment_file = request.FILES.get('attachments')
                if attachment_file:
                    try:
                        support_attachment = SupportAttachment(
                            ticket=ticket,
                            file=attachment_file,
                            file_name=attachment_file.name,  
                            file_size=attachment_file.size
                        )
                        support_attachment.save()
                        
                    except Exception as e:
                        messages.error(request, f'Ошибка сохранения вложения')
                
                ticket_attachments = SupportAttachment.objects.filter(ticket=ticket)
                send_support_notification(ticket, list(ticket_attachments))
                
                messages.success(request, '✅ Ваше обращение успешно отправлено! Мы свяжемся с вами в ближайшее время.')
                return redirect('support')
                
            except Exception as e:
                messages.error(request, f'❌ Произошла ошибка при отправке обращения: {str(e)}')
        else:
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_messages.append(f"{field}: {error}")
            
            if error_messages:
                messages.error(request, f'❌ Ошибки: {" | ".join(error_messages)}')
            else:
                messages.error(request, '❌ Пожалуйста, исправьте ошибки в форме.')
    else:
        form = SupportTicketForm()
    
    context = {
        'form': form,
        'active_tab': 'support'
    }
    return render(request, 'main/support.html', context)
    
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
                return True
            else:
                return False
                
    except Exception as e:
        return False

def check_bot_settings():
    """Проверка настроек бота"""
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            bot_info = response.json()
            return True
        else:
            return False
    except Exception as e:
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
        
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code != 200:
            return send_fallback_notification(ticket, attachments)
            
        for attachment in attachments:
            try:
                send_attachment_with_quality(attachment, chat_id)
            except Exception as e:
                return False
        
        NotificationLog.objects.create(
            notification_type='support_ticket',
            message=f'Заявка поддержки #{ticket.id} отправлена в Telegram ({ "CRITICAL" if ticket.priority == "critical" else "NORMAL" })',
            sent_to=f"Telegram: {chat_id}",
            success=True
        )
        
        return True
        
    except Exception as e:
        return send_fallback_notification(ticket, attachments)

def parse_user_agent(user_agent):
    """Парсинг User-Agent для получения информации о браузере и ОС"""
    try:
        ua = user_agent.lower()
        browser_info = {}
        
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
        
        if 'mobile' in ua:
            browser_info['device'] = 'Мобильное'
        elif 'tablet' in ua:
            browser_info['device'] = 'Планшет'
        else:
            browser_info['device'] = 'Десктоп'
            
        return browser_info
        
    except Exception as e:
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
            'host': 'tech-re.ru',  
            'path': '/support/',
            'referer': 'Прямой заход',
            'cookies_enabled': 'Да (предположительно)',
            'javascript_enabled': 'Да (предположительно)',
            'screen_resolution': 'Неизвестно',
            'timezone': 'Неизвестно'
        }
        
        return info
        
    except Exception as e:
        return {}

def send_attachment_with_quality(attachment, chat_id):
    """Отправка вложения с сохранением качества фото"""
    try:
        file_path = attachment.file.path
        file_name = attachment.file_name.lower()
        
        if any(ext in file_name for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"
            
            with open(file_path, 'rb') as file:
                files = {'document': file}
                data = {
                    'chat_id': chat_id,
                    'caption': f'Файл к обращению: {attachment.file_name}'
                }
                
                response = requests.post(url, data=data, files=files, timeout=30)
        else:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"
            
            with open(file_path, 'rb') as file:
                files = {'document': file}
                data = {
                    'chat_id': chat_id,
                    'caption': f'📎 {attachment.file_name}'
                }
                
                response = requests.post(url, data=data, files=files, timeout=30)
        
        if response.status_code == 200:
            return True
        else:
            return False
            
    except Exception as e:
        return False

def send_fallback_notification(ticket, attachments):
    """Резервный метод отправки уведомления"""
    try:
        if ticket.priority == 'critical':
            chat_id = settings.TELEGRAM_CHAT_ID_CRITICAL
            prefix = "🚨🚨🚨 КРИТИЧЕСКАЯ ЗАЯВКА: "
        else:
            chat_id = settings.TELEGRAM_CHAT_ID_CONTACTS
            prefix = "🆘 Новая заявка поддержки: "
        
        message = f"{prefix}#{ticket.id}\nТема: {ticket.subject}\nПриоритет: {ticket.get_priority_display()}"
        
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return True
        else:
            return False
            
    except Exception as e:
        return False
    
def send_attachment_to_telegram(attachment):
    """Отправка вложения в Telegram"""
    try:
        file_path = attachment.file.path
        
        file_extension = attachment.file_name.lower().split('.')[-1] if attachment.file_name else 'bin'
        
        if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendPhoto"
            files = {'photo': open(file_path, 'rb')}
            data = {
                'chat_id': settings.TELEGRAM_CHAT_ID_CONTACTS,
                'caption': f'📎 {attachment.file_name}'
            }
        elif file_extension in ['mp4', 'avi', 'mov', 'webm']:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendVideo"
            files = {'video': open(file_path, 'rb')}
            data = {
                'chat_id': settings.TELEGRAM_CHAT_ID_CONTACTS,
                'caption': f'🎥 {attachment.file_name}'
            }
        else:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"
            files = {'document': open(file_path, 'rb')}
            data = {
                'chat_id': settings.TELEGRAM_CHAT_ID_CONTACTS,
                'caption': f'📄 {attachment.file_name}'
            }
        
        response = requests.post(url, data=data, files=files, timeout=30)
        
        file_key = list(files.keys())[0]
        files[file_key].close()
        
        if response.status_code != 200:
            return False
            
        return True
        
    except Exception as e:
        return False
    
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
            page = ServicePage.objects.get(
                slug=instruction_slug,
                page_type='instruction',
                parent__slug=sub_slug,
                parent__parent__slug=service_slug,
                is_active=True
            )
        elif sub_slug:
            page = ServicePage.objects.get(
                slug=sub_slug,
                page_type='sub_service', 
                parent__slug=service_slug,
                is_active=True
            )
        else:
            page = ServicePage.objects.get(
                slug=service_slug,
                page_type='main_service',
                is_active=True
            )
        
    except ServicePage.DoesNotExist:
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
    """Исправленная отправка email - используем Python EmailMessage напрямую"""
    try:
        import smtplib
        from email.message import EmailMessage
        from email.header import Header
        from email.utils import formataddr
        
        msg = EmailMessage()
        
        # Текстовое содержимое
        text_content = f"""Код восстановления пароля - Техресурс

Здравствуйте, {username}!

Ваш код восстановления: {code}

Код действителен в течение 10 минут.

Если вы не запрашивали восстановление пароля, проигнорируйте это письмо.

С уважением,
Команда Техресурс
"""
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #0052cc; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background: #f8f9fa; }}
        .code {{ font-size: 24px; font-weight: bold; color: #0052cc; text-align: center; margin: 20px 0; padding: 15px; background: white; border: 2px dashed #0052cc; }}
        .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
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
</html>"""
        
        msg.set_content(text_content)
        msg.add_alternative(html_content, subtype='html')
        
        msg['From'] = 'noreply@tech-re.ru'
        msg['To'] = email
        msg['Subject'] = 'Код восстановления пароля - Техресурс'
        msg['X-Mailer'] = 'Django App'
        
        # Отправляем
        with smtplib.SMTP('127.0.0.1', 25) as server:
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        try:
            import subprocess
            
            email_text = f"""From: noreply@tech-re.ru
To: {email}
Subject: Код восстановления пароля - Техресурс

Код восстановления: {code}
Действителен 10 минут."""
            
            result = subprocess.run(
                ['mail', '-s', 'Код восстановления пароля - Техресурс', '-r', 'noreply@tech-re.ru', email],
                input=email_text.encode('utf-8'),
                capture_output=True,
                text=False
            )
            
            if result.returncode == 0:
                return True
            else:
                return False
                
        except Exception as fallback_e:
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
        
        return True
        
    except Exception as e:
        return False

def check_rate_limit(email, action, limit=3, timeout=300):
    """Проверка частоты запросов с указанием действия"""
    key = f"rate_limit_{action}_{email}"
    attempts = cache.get(key, 0)
    
    if attempts >= limit:
        return False
    
    cache.set(key, attempts + 1, timeout)
    return True

def send_invoice_email(order):
    """Отправка счета на email покупателя с PDF вложением"""
    try:
        invoice_number = order.generate_invoice_number()
        order_items = order.orderitem_set.all()
        due_date = order.get_due_date()
        
        company_info = {
            'name': 'Техресурс',
            'inn': '1684010655',
            'kpp': '168401001',
            'ogrn': '1231600004712',
            'legal_address': '422527 Республика Татарстан, ул. Техническая, зд. 52, офис 226',
            'postal_address': '422527 Республика Татарстан, ул. Техническая, зд. 52, офис 226',
            'bank_account': '40702810129930004534',
            'bank_name': 'ФИЛИАЛ "НИЖЕГОРОДСКИЙ" АО "АЛЬФА-БАНК"',
            'bik': '042202824',
            'correspondent_account': '30101810200000000824',
            'director': 'Казначеев Анатолий Андреевич',
            'phone': '+7 (937) 524-68-88',
            'email': 'Kaznacheev56@gmail.com',
        }

        qr_code_data = generate_payment_qr_code(order, company_info)
        
        buyer_info = {
            'name': order.customer_name,
            'inn': order.customer_inn,
            'kpp': order.customer_kpp or '',
            'address': order.delivery_address,
            'contact_name': order.customer_name,
            'phone': order.customer_phone,
            'email': order.customer_email,
        }
        
        items_data = []
        for index, order_item in enumerate(order_items, 1):
            item_price_in_rub = order_item.product.get_display_price('RUB')
            item_total_rub = order_item.quantity * item_price_in_rub
            vat_amount_rub = item_total_rub * order_item.vat_rate / (100 + order_item.vat_rate)
            
            items_data.append({
                'index': index,
                'description': order_item.product.name,
                'sku': order_item.product.article or '',
                'quantity': order_item.quantity,
                'unit': 'шт.',
                'unit_price': item_price_in_rub,  
                'line_total': item_total_rub,  
                'vat': vat_amount_rub, 
                'vat_rate': order_item.vat_rate,
            })
        
        
        totals = {
            'net': order.price_without_vat,
            'vat': order.vat_amount,
            'gross': order.total_price,
            'vat_rate': order.vat_rate,
        }
        
        context = {
            'order': order,
            'invoice_number': invoice_number,
            'invoice_date': order.invoice_date.strftime('%d.%m.%Y'),
            'due_date': due_date.strftime('%d.%m.%Y'),
            'company': company_info,
            'buyer': buyer_info,
            'totals': totals,
            'items': items_data,
            'invoice_validity_days': 5,
            'qr_code': qr_code_data,
        }
        
        html_content = render_to_string('main/invoice_email.html', context)
        pdf_file = generate_pdf_from_html(html_content, order, invoice_number)
        
        if not pdf_file:
            raise Exception("Не удалось сгенерировать PDF файл")
        
        subject = f"Счет на оплату №{invoice_number} от {order.invoice_date.strftime('%d.%m.%Y')} - Техресурс"
        
        plain_message = f"""
Здравствуйте, {order.customer_name}!

Во вложении вы найдете счет на оплату №{invoice_number} от {order.invoice_date.strftime('%d.%m.%Y')}.

Пожалуйста, оплатите счет в течение {5} банковских дней.

Если у вас возникли вопросы, свяжитесь с нами:
Телефон: {company_info['phone']}
Email: {company_info['email']}

С уважением,
Команда Техресурс

Это сообщение создано автоматически, не нужно отвечать на него
"""
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.customer_email],
            reply_to=['noreply@tech-re.ru'],
            headers={
                'X-Priority': '1',
                'X-MSMail-Priority': 'High',
                'Importance': 'High'
            }
        )
        
        pdf_filename = f"Счет_{invoice_number}_{order.customer_name.replace(' ', '_')}.pdf"
        email.attach(pdf_filename, pdf_file.getvalue(), 'application/pdf')
        email.send(fail_silently=False)
        telegram_sent = send_invoice_to_telegram_with_info(pdf_file.getvalue(), pdf_filename, order, company_info)
        order.invoice_sent = True
        order.invoice_sent_at = timezone.now()
        order.invoice_pdf_sent_to_telegram = telegram_sent
        order.save()
        
        NotificationLog.objects.create(
            order=order,
            notification_type='invoice_sent',
            message=f'Счет №{invoice_number} отправлен на {order.customer_email} с PDF вложением',
            sent_to=order.customer_email,
            success=True
        )
        
        pdf_file.close()
        
        return True
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        NotificationLog.objects.create(
            order=order,
            notification_type='invoice_sent',
            message=f'Ошибка отправки счета с PDF: {str(e)}',
            sent_to=order.customer_email,
            success=False,
            error_message=str(e)
        )
        
        return False
    
def send_invoice_to_telegram_with_info(pdf_bytes, filename, order, company_info):
    """Отправка PDF файла в Telegram с информацией о заказе в одном сообщении"""
    try:
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            return False
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(pdf_bytes)
            temp_file_path = temp_file.name
        
        try:
            message = f"""
📄 <b>СЧЕТ НА ОПЛАТУ #{order.invoice_number}</b>

<b>📅 Дата:</b> {order.invoice_date.strftime('%d.%m.%Y')}
<b>⏰ Срок оплаты:</b> {order.get_due_date().strftime('%d.%m.%Y')}

<b>🏢 Поставщик:</b> {company_info['name']}
<b>📋 ИНН/КПП:</b> {company_info['inn']}/{company_info['kpp']}

<b>👤 Покупатель:</b> {order.customer_name}
<b>📋 ИНН:</b> {order.customer_inn}
<b>📍 КПП:</b> {order.customer_kpp or 'Не указан'}
<b>📧 Email:</b> {order.customer_email}
<b>📞 Телефон:</b> {order.customer_phone}

<b>💰 Сумма:</b> {order.total_price} руб.
<b>🏛️ Без НДС:</b> {int(order.price_without_vat)} руб.
<b>📊 НДС ({order.vat_rate}%):</b> {int(order.vat_amount)} руб.

<b>🚚 Адрес доставки:</b>
{order.delivery_address}

<b>🏦 Назначение платежа:</b>
Оплата по счету №{order.invoice_number} от {order.invoice_date.strftime('%d.%m.%Y')}

<b>📋 Контакты для связи:</b>
📞 Телефон: {order.customer_phone}
✉️ Email: {order.customer_email}
👤 Контактное лицо: {order.customer_name}

<b>⏰ Время создания:</b> {timezone.now().strftime('%d.%m.%Y %H:%M')}
"""
            
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"
            
            with open(temp_file_path, 'rb') as file:
                files = {'document': (filename, file)}
                data = {
                    'chat_id': settings.TELEGRAM_CHAT_ID,
                    'caption': message,
                    'parse_mode': 'HTML',
                    'disable_web_page_preview': True
                }
                
                response = requests.post(url, files=files, data=data, timeout=30)
                
                if response.status_code == 200:
                    
                    NotificationLog.objects.create(
                        order=order,
                        notification_type='invoice_pdf_telegram',
                        message=f'PDF счета №{order.invoice_number} с информацией о заказе отправлен в Telegram',
                        sent_to=f"Telegram: {settings.TELEGRAM_CHAT_ID}",
                        success=True
                    )
                    
                    return True
                else:
                    return False
                    
        finally:
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                return False
                
    except Exception as e:
        
        NotificationLog.objects.create(
            order=order,
            notification_type='invoice_pdf_telegram',
            message=f'Ошибка отправки PDF в Telegram: {str(e)}',
            sent_to=f"Telegram: {settings.TELEGRAM_CHAT_ID}",
            success=False,
            error_message=str(e)
        )
        
        return False

def generate_pdf_from_html(html_content, order, invoice_number):
    """Генерация PDF из HTML с использованием WeasyPrint"""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as html_file:
            html_file.write(html_content)
            html_file_path = html_file.name
        
        try:
            pdf_file = BytesIO()
            HTML(filename=html_file_path).write_pdf(
                pdf_file,
                stylesheets=[
                    CSS(string='''
                        @page {
                            size: A4;
                            margin: 18mm;
                            @bottom-center {
                                content: "Страница " counter(page) " из " counter(pages);
                                font-size: 10px;
                                color: #666;
                            }
                        }
                        
                        body {
                            font-family: "DejaVu Sans", "Arial", sans-serif;
                            font-size: 11pt;
                            line-height: 1.4;
                        }
                        
                        table.items {
                            page-break-inside: avoid;
                        }
                        
                        .items th, .items td {
                            padding: 6px 8px;
                        }
                        
                        .items {
                            border: 1px solid #000 !important;
                        }
                        
                        .items th, .items td {
                            border: 1px solid #000 !important;
                        }
                        
                        .summary .total {
                            font-weight: bold;
                            font-size: 14pt;
                        }
                        
                        @media print {
                            .sheet {
                                box-shadow: none !important;
                                margin: 0 !important;
                            }
                            
                            .viewport {
                                padding: 0 !important;
                            }
                        }
                    ''')
                ],
                presentational_hints=True,
                optimize_size=('fonts', 'images')
            )
            
            pdf_file.seek(0)
            return pdf_file
            
        finally:
            try:
                os.unlink(html_file_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Ошибка генерации PDF для заказа {order.id}: {str(e)}")
        
        try:
            pdf_file = BytesIO()
            HTML(string=html_content).write_pdf(pdf_file)
            pdf_file.seek(0)
            return pdf_file
        except Exception as alt_e:  
            return None

def get_anonymous_cart(request):
    """Получение анонимной корзины из сессии"""
    
    if 'anonymous_cart' not in request.session:
        request.session['anonymous_cart'] = {}
    
    cart = request.session['anonymous_cart']
    return cart

def anonymous_cart_items(request):
    """API: Получение товаров в анонимной корзине"""
    cart = get_anonymous_cart(request)
    items = []
    total = Decimal('0')
    
    for product_id, item_data in cart.items():
        try:
            product = Product.objects.get(id=product_id)
            quantity = item_data['quantity']
            price_in_rub = product.get_display_price('RUB')
            item_total = price_in_rub * quantity
            
            items.append({
                'product_id': product.id,
                'name': product.name,
                'article': product.article,
                'price': float(price_in_rub), 
                'quantity': quantity,
                'total': float(item_total),    
                'image': product.get_display_image_url(),
                'max_quantity': product.quantity
            })
            total += item_total
        except Product.DoesNotExist:
            continue
    
    return JsonResponse({
        'success': True,
        'items': items,
        'total': str(total),
        'count': len(cart)
    })

def anonymous_add_to_cart(request, product_id):
    """API: Добавление товара в анонимную корзину"""
    if request.method == 'POST':
        try:
            product = Product.objects.get(id=product_id, is_active=True)
            quantity = int(request.POST.get('quantity', 1))
            
            cart = get_anonymous_cart(request)
            product_key = str(product_id)
            
            if product_key in cart:
                new_quantity = cart[product_key]['quantity'] + quantity
                if new_quantity > product.quantity:
                    return JsonResponse({
                        'success': False,
                        'error': f'Максимальное количество: {product.quantity}'
                    })
                cart[product_key]['quantity'] = new_quantity
            else:
                if quantity > product.quantity:
                    return JsonResponse({
                        'success': False,
                        'error': f'Максимальное количество: {product.quantity}'
                    })
                cart[product_key] = {
                    'product_id': product_id,
                    'quantity': quantity,
                    'added_at': timezone.now().isoformat()
                }
            
            request.session['anonymous_cart'] = cart
            request.session.modified = True
            
            cart_count = sum(item['quantity'] for item in cart.values())
            
            return JsonResponse({
                'success': True,
                'cart_count': cart_count,
                'message': 'Товар добавлен в заказ'
            })
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Товар не найден'
            })
    
    return JsonResponse({'success': False, 'error': 'Неверный запрос'})

def anonymous_update_cart(request):
    """API: Обновление количества товара в анонимной корзине"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = str(data.get('product_id'))
            delta = data.get('delta', 0)
            new_quantity = data.get('quantity')
            
            cart = get_anonymous_cart(request)
            
            if product_id not in cart:
                return JsonResponse({'success': False, 'error': 'Товар не найден в заказе'})
            
            product = Product.objects.get(id=int(product_id))
            
            if new_quantity is not None:
                quantity = int(new_quantity)
            else:
                quantity = cart[product_id]['quantity'] + delta
            
            if quantity < 1:
                del cart[product_id]
            else:
                if quantity > product.quantity:
                    return JsonResponse({
                        'success': False,
                        'error': f'Максимальное количество: {product.quantity}'
                    })
                cart[product_id]['quantity'] = quantity
            
            request.session['anonymous_cart'] = cart
            request.session.modified = True
            
            cart_count = sum(item['quantity'] for item in cart.values())
            
            return JsonResponse({
                'success': True,
                'cart_count': cart_count
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Неверный запрос'})

def anonymous_remove_from_cart(request):
    """API: Удаление товара из анонимной корзины"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = str(data.get('product_id'))
            
            cart = get_anonymous_cart(request)
            
            if product_id in cart:
                del cart[product_id]
                request.session['anonymous_cart'] = cart
                request.session.modified = True
            
            cart_count = sum(item['quantity'] for item in cart.values())
            
            return JsonResponse({
                'success': True,
                'cart_count': cart_count
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Неверный запрос'})

def anonymous_order_page(request):
    """Страница оформления анонимного заказа"""
    cart = get_anonymous_cart(request)
    
    if not cart:
        messages.info(request, 'Добавьте товары для оформления заказа')
        return redirect('products')
    
    return render(request, 'main/anonymous_order.html')

def anonymous_create_order(request):
    """Создание анонимного заказа (оплата по счету)"""
    if request.method == 'POST':
        try:
            cart = get_anonymous_cart(request)
            
            
            if not cart:
                return JsonResponse({
                    'success': False,
                    'error': 'Заказ пуст'
                })
            
            for product_id, item_data in cart.items():
                try:
                    product = Product.objects.get(id=int(product_id))
                    if product.quantity < item_data['quantity']:
                        return JsonResponse({
                            'success': False,
                            'error': f'Недостаточно товара "{product.name}" на складе. Доступно: {product.quantity}'
                        })
                except Product.DoesNotExist:
                    continue

            required_fields = ['contact_person', 'phone', 'email', 'company_name', 'inn', 
                              'legal_address', 'delivery_address']
            
            missing_fields = []
            for field in required_fields:
                value = request.POST.get(field, '').strip()
                if not value:
                    missing_fields.append(field)
            
            if missing_fields:
                return JsonResponse({
                    'success': False,
                    'error': f'Заполните обязательные поля: {", ".join(missing_fields)}'
                })
            
            inn = request.POST.get('inn', '').strip()
            if not inn.isdigit() or len(inn) not in [10, 12]:
                return JsonResponse({
                    'success': False,
                    'error': 'ИНН должен содержать 10 или 12 цифр'
                })
            
            customer_email = request.POST.get('email', '').strip()
            if not customer_email or '@' not in customer_email:
                return JsonResponse({
                    'success': False,
                    'error': 'Введите корректный email адрес'
                })
            
            total = Decimal('0')
            order_items_data = []
            
            for product_id, item_data in cart.items():
                try:
                    product = Product.objects.get(id=int(product_id))
                    quantity = item_data['quantity']
                    price_in_rub = product.get_display_price('RUB')
                    item_total = price_in_rub * quantity
                    total += item_total
                    
                    order_items_data.append({
                        'product': product,
                        'quantity': quantity,
                        'price': price_in_rub,
                        'total': item_total
                    })
                    
                except Product.DoesNotExist:
                    continue
            
            
            if total == Decimal('0'):
                return JsonResponse({
                    'success': False,
                    'error': 'Некорректная сумма заказа'
                })
            
            vat_rate = Decimal('22.00')
            vat_amount = total * vat_rate / Decimal('122.00')
            price_without_vat = total - vat_amount
            
            from datetime import datetime
            current_year = datetime.now().year
            order_count = Order.objects.filter(invoice_date__year=current_year).count()
            invoice_number = f"{datetime.now().strftime('%Y%m')}-{order_count + 1:04d}"
            
            order = Order.objects.create(
                user=None,  
                total_price=total,
                final_price=total,
                price_without_vat=price_without_vat,
                vat_amount=vat_amount,
                vat_rate=vat_rate,
                payment_method='invoice',
                payment_fee=Decimal('0'),
                delivery_cost=Decimal('0'),
                customer_name=request.POST.get('contact_person', '').strip(),
                customer_phone=request.POST.get('phone', '').strip(),
                customer_email=customer_email,
                customer_inn=inn,
                customer_kpp=request.POST.get('kpp', '').strip(),
                delivery_address=request.POST.get('delivery_address', '').strip(),
                status='processing',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                invoice_date=timezone.now().date(),
                invoice_sent=False,
            )

            order.invoice_number = order.generate_invoice_number()
            order.save(update_fields=['invoice_number'])

            for item_data in order_items_data:
                try:
                    order_item = OrderItem.objects.create(
                        order=order,
                        product=item_data['product'],
                        quantity=item_data['quantity'],
                        price=item_data['price'],
                        vat_rate=vat_rate,
                    )
                    
                    product = item_data['product']
                    product.quantity -= item_data['quantity']
                    product.save()
                    
                except Exception as e:
                    return False
            
            telegram_success = False
            request.session['anonymous_cart'] = {}
            request.session.modified = True
            try:
                telegram_data = {
                    'contact_person': order.customer_name,
                    'phone': order.customer_phone,
                    'email': order.customer_email,
                    'company_name': request.POST.get('company_name', ''),
                    'inn': order.customer_inn,
                    'kpp': order.customer_kpp,
                    'legal_address': request.POST.get('legal_address', ''),
                    'delivery_address': order.delivery_address,
                    'comment': request.POST.get('comment', ''),
                    'total': str(total),
                    'invoice_number': order.invoice_number,
                    'items': [{
                        'name': item['product'].name,
                        'article': item['product'].article,
                        'quantity': item['quantity'],
                        'total': str(item['total'])
                    } for item in order_items_data]
                }
            except Exception as e:
                telegram_success = False
            try:
                email_success = send_invoice_email(order)
                
                if email_success:
                    order.invoice_sent = True
                    order.invoice_sent_at = timezone.now()
                    order.save(update_fields=['invoice_sent', 'invoice_sent_at'])
            except Exception as e:
                import traceback
                traceback.print_exc()
                email_success = False
            
            if email_success:
                return JsonResponse({
                    'success': True,
                    'message': f'✅ Заявка отправлена! Счет №{order.invoice_number} выслан на {order.customer_email}',
                    'email_sent': True,
                    'telegram_sent': telegram_success,
                    'order_id': order.id,
                    'invoice_number': order.invoice_number
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': f'⚠️ Заявка отправлена! Заказ #{order.id} создан. Для получения счета свяжитесь с нами по телефону.',
                    'email_sent': False,
                    'telegram_sent': telegram_success,
                    'order_id': order.id,
                    'invoice_number': order.invoice_number
                })
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            
            return JsonResponse({
                'success': False,
                'error': f'Произошла ошибка: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})


def send_file_to_telegram(file_path, file_name, caption=None):
    """Отправка файла в Telegram"""
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"
        
        with open(file_path, 'rb') as file:
            files = {'document': (file_name, file)}
            data = {
                'chat_id': settings.TELEGRAM_CHAT_ID,
                'caption': caption or file_name
            }
            
            response = requests.post(url, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                return True
            else:
                return False
                
    except Exception as e:
        return False
    
def generate_payment_qr_code(order, company_info):
    """
    Платёжный QR по ГОСТ Р 56042-2014 (ST00012)
    Работает без СБП и без API банка
    """

    amount_kopecks = int(order.total_price * 100)

    qr_text = (
        "ST00012|"
        f"Name={company_info['name']}|"
        f"PersonalAcc={company_info['bank_account']}|"
        f"BankName={company_info['bank_name']}|"
        f"BIC={company_info['bik']}|"
        f"CorrespAcc={company_info['correspondent_account']}|"
        f"PayeeINN={company_info['inn']}|"
        f"Purpose=Оплата счета №{order.invoice_number} от "
        f"{order.invoice_date.strftime('%d.%m.%Y')}|"
        f"Sum={amount_kopecks}"
    )

    qr = qrcode.QRCode(
        version=5,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=1,
    )

    qr.add_data(qr_text)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")

    img_base64 = base64.b64encode(buffer.getvalue()).decode()

    return {
        'qr_image': f"data:image/png;base64,{img_base64}",
        'qr_text': qr_text
    }

@login_required
def profile_settings(request):
    """Настройки профиля пользователя"""
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Настройки профиля сохранены')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Настройки сохранены',
                    'avatar_url': profile.avatar.url if profile.avatar else None
                })
            
            return redirect('profile_settings')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
    else:
        form = UserProfileForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
        'active_tab': 'settings'
    }
    return render(request, 'main/profile_settings.html', context)

def public_profile(request, slug_or_id):
    """Публичный профиль пользователя"""
    try:
        if slug_or_id.isdigit():
            profile = get_object_or_404(UserProfile, user_id=int(slug_or_id))
        else:
            profile = get_object_or_404(UserProfile, profile_slug=slug_or_id)
    except (ValueError, UserProfile.DoesNotExist):
        raise Http404("Профиль не найден")
    
    if not profile.can_view_profile(request.user):
        raise Http404("Профиль недоступен")
    
    visible_fields = profile.get_visible_fields(request.user)
    
    recent_activity = []
    
    if profile.can_view_field(request.user, 'activity'):
        recent_articles = BlogArticle.objects.filter(
            author=profile.user,
            status='published'
        ).select_related('category').order_by('-published_at')[:5]
        
        recent_comments = BlogComment.objects.filter(
            user=profile.user,
            status='approved'
        ).select_related('article').order_by('-created_at')[:5]
        
        recent_reviews = ProductReview.objects.filter(
            user=profile.user,
            is_approved=True
        ).select_related('product').order_by('-created_at')[:5]
        
        for article in recent_articles:
            recent_activity.append({
                'type': 'article',
                'title': article.title,
                'description': article.excerpt[:100] + '...' if len(article.excerpt) > 100 else article.excerpt,
                'date': article.published_at,
                'url': article.get_absolute_url()
            })
        
        for comment in recent_comments:
            recent_activity.append({
                'type': 'comment',
                'title': f'Комментарий к "{comment.article.title}"',
                'description': comment.content[:100] + '...' if len(comment.content) > 100 else comment.content,
                'date': comment.created_at,
                'url': comment.article.get_absolute_url() + '#comment-' + str(comment.id)
            })
        
        for review in recent_reviews:
            recent_activity.append({
                'type': 'review',
                'title': f'Отзыв на "{review.product.name}"',
                'description': f'Оценка: {review.rating}/5',
                'date': review.created_at,
                'url': reverse('product_detail', kwargs={'product_id': review.product.id}) + '#reviews'
            })
        
        recent_activity.sort(key=lambda x: x['date'], reverse=True)
        recent_activity = recent_activity[:10]  
    
    context = {
        'profile_user': profile.user,
        'profile': profile,
        'visible_fields': visible_fields,
        'recent_activity': recent_activity,
        'is_owner': request.user == profile.user,
        'can_edit': request.user.is_staff or request.user == profile.user,
    }
    
    return render(request, 'main/public_profile.html', context)

@staff_member_required
def admin_profile_manage(request, user_id):
    """Управление профилем пользователя (админка)"""
    profile = get_object_or_404(UserProfile, user_id=user_id)
    
    if request.method == 'POST':
        form = AdminProfileTagsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f'Теги профиля для {profile.user.username} обновлены')
            return redirect('admin_profile_manage', user_id=user_id)
    else:
        form = AdminProfileTagsForm(instance=profile)
    
    context = {
        'profile': profile,
        'form': form,
        'user': profile.user
    }
    return render(request, 'main/admin_profile_manage.html', context)

@login_required
def profile_preview(request):
    """Превью профиля (как его видят другие)"""
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    class PreviewUser:
        def __init__(self, user):
            self.username = user.username
            self.first_name = user.first_name
            self.last_name = user.last_name
            self.email = user.email
            self.date_joined = user.date_joined
            self.is_staff = user.is_staff
    
    preview_user = PreviewUser(request.user)
    
    context = {
        'profile_user': preview_user,
        'profile': profile,
        'skills': profile.get_skills_list(),
        'tags': profile.get_public_tags(),
        'is_preview': True,
        'privacy_mode': profile.privacy_mode,
    }
    
    return render(request, 'main/public_profile.html', context)

@login_required
def update_profile_field(request):
    """AJAX обновление отдельного поля профиля"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Invalid request'})
    
    try:
        data = json.loads(request.body)
        field = data.get('field')
        value = data.get('value')
        
        if not field or value is None:
            return JsonResponse({'success': False, 'error': 'Missing field or value'})
        
        profile = UserProfile.objects.get(user=request.user)
        
        allowed_fields = [
            'public_bio', 'public_skills', 'profile_theme',
            'show_statistics', 'show_recent_activity'
        ]
        
        if field not in allowed_fields:
            return JsonResponse({'success': False, 'error': 'Field not allowed'})
        
        if field == 'public_bio' and len(value) > 1000:
            return JsonResponse({'success': False, 'error': 'Bio too long'})
        
        if field == 'public_skills':
            skills_list = [s.strip() for s in value.split(',') if s.strip()]
            if len(skills_list) > 20:
                return JsonResponse({'success': False, 'error': 'Too many skills'})
        
        setattr(profile, field, value)
        profile.save(update_fields=[field, 'last_profile_update'])
        
        return JsonResponse({'success': True, 'message': 'Updated'})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Profile not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def profile_card(request, user_id):
    """Виджет профиля для вставки в блог/комментарии"""
    try:
        profile = UserProfile.objects.get(user_id=user_id)
        
        if not profile.can_view_profile(request.user):
            return JsonResponse({'success': False, 'error': 'Profile not available'})
        
        context = {
            'profile_user': profile.user,
            'profile': profile,
            'is_card': True
        }
        
        from django.template.loader import render_to_string
        html = render_to_string('main/components/profile_card.html', context)
        
        return JsonResponse({
            'success': True,
            'html': html,
            'username': profile.user.username,
            'avatar_url': profile.avatar_small.url if profile.avatar_small else None
        })
    
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Profile not found'})

@login_required
def upload_avatar(request):
    """Отдельная загрузка аватара"""
    if request.method == 'POST' and request.FILES.get('avatar'):
        try:
            profile = UserProfile.objects.get(user=request.user)
            
            from .validators import validate_avatar
            avatar = request.FILES['avatar']
            
            try:
                validate_avatar(avatar)
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
            
            profile.avatar = avatar
            profile.save()
            
            return JsonResponse({
                'success': True,
                'avatar_url': profile.avatar.url,
                'avatar_small_url': profile.avatar_small.url if profile.avatar_small else None,
                'avatar_medium_url': profile.avatar_medium.url if profile.avatar_medium else None,
                'avatar_large_url': profile.avatar_large.url if profile.avatar_large else None,
            })
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

from datetime import datetime, date
from django.db.models import Q, Sum, Count

@staff_member_required
def invoice_registry(request):
    """Главная страница реестра счетов"""
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('search', '')
    
    invoices = InvoiceRegistry.objects.all().select_related('order')
    
    if status_filter:
        invoices = invoices.filter(status=status_filter)
    
    if date_from:
        try:
            invoices = invoices.filter(invoice_date__gte=date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            invoices = invoices.filter(invoice_date__lte=date_to)
        except ValueError:
            pass
    
    if search_query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_inn__icontains=search_query) |
            Q(customer_email__icontains=search_query)
        )
    
    stats = {
        'total': invoices.count(),
        'total_amount': invoices.aggregate(Sum('amount'))['amount__sum'] or 0,
        'total_paid': invoices.filter(status='paid').aggregate(Sum('amount'))['amount__sum'] or 0,
        'total_overdue': invoices.filter(status='overdue').aggregate(Sum('amount'))['amount__sum'] or 0,
        'overdue_count': invoices.filter(status='overdue').count(),
    }
    
    paginator = Paginator(invoices, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'invoices': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
        'stats': stats,
        'status_choices': InvoiceRegistry.STATUS_CHOICES,
    }
    
    return render(request, 'main/invoice_registry.html', context)

@staff_member_required
def export_invoices_excel(request):
    """Экспорт реестра в Excel"""
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    invoices = InvoiceRegistry.objects.all()
    
    if status_filter:
        invoices = invoices.filter(status=status_filter)
    if date_from:
        invoices = invoices.filter(invoice_date__gte=date_from)
    if date_to:
        invoices = invoices.filter(invoice_date__lte=date_to)
    
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Реестр счетов')
    
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4472C4',
        'font_color': 'white',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    date_format = workbook.add_format({'num_format': 'dd.mm.yyyy'})
    money_format = workbook.add_format({'num_format': '#,##0.00'})
    
    headers = [
        '№', 'Номер счета', 'Дата счета', 'Срок оплаты', 
        'Покупатель', 'ИНН', 'Email', 'Телефон',
        'Сумма', 'НДС', 'Без НДС', 'Статус',
        'Email отправлен', 'Telegram отправлен', 'Заказ №', 'Просрочено дней'
    ]
    
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    
    for row, invoice in enumerate(invoices, start=1):
        worksheet.write(row, 0, row)
        worksheet.write(row, 1, invoice.invoice_number)
        worksheet.write(row, 2, invoice.invoice_date, date_format)
        worksheet.write(row, 3, invoice.due_date, date_format)
        worksheet.write(row, 4, invoice.customer_name)
        worksheet.write(row, 5, invoice.customer_inn or '')
        worksheet.write(row, 6, invoice.customer_email)
        worksheet.write(row, 7, invoice.customer_phone)
        worksheet.write(row, 8, float(invoice.amount), money_format)
        worksheet.write(row, 9, float(invoice.vat_amount), money_format)
        worksheet.write(row, 10, float(invoice.amount_without_vat), money_format)
        
        status_format = workbook.add_format()
        if invoice.status == 'paid':
            status_format.set_bg_color('#C6EFCE')
        elif invoice.status == 'overdue':
            status_format.set_bg_color('#FFC7CE')
        elif invoice.status == 'sent':
            status_format.set_bg_color('#FFEB9C')
        
        worksheet.write(row, 11, invoice.get_status_display(), status_format)
        worksheet.write(row, 12, 'Да' if invoice.email_sent else 'Нет')
        worksheet.write(row, 13, 'Да' if invoice.telegram_sent else 'Нет')
        worksheet.write(row, 14, invoice.order.id)
        worksheet.write(row, 15, invoice.get_overdue_days() if invoice.is_overdue() else 0)
    
    for col in range(len(headers)):
        worksheet.set_column(col, col, 15)
    
    worksheet.set_column(4, 4, 25)  
    
    total_row = len(invoices) + 2
    worksheet.write(total_row, 7, 'ИТОГО:', header_format)
    worksheet.write(total_row, 8, f'=SUM(I2:I{len(invoices)+1})', money_format)
    
    workbook.close()
    output.seek(0)
    
    filename = f'reestr_schetov_{date.today().strftime("%Y%m%d")}.xlsx'
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@staff_member_required
def send_invoice_report_telegram(request):
    """Отправка отчета по счетам в Telegram"""
    try:
        status_filter = request.GET.get('status', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        
        invoices = InvoiceRegistry.objects.all()
        
        if status_filter:
            invoices = invoices.filter(status=status_filter)
        if date_from:
            invoices = invoices.filter(invoice_date__gte=date_from)
        if date_to:
            invoices = invoices.filter(invoice_date__lte=date_to)
        
        total_count = invoices.count()
        total_amount = invoices.aggregate(Sum('amount'))['amount__sum'] or 0
        paid_amount = invoices.filter(status='paid').aggregate(Sum('amount'))['amount__sum'] or 0
        overdue_count = invoices.filter(status='overdue').count()
        overdue_amount = invoices.filter(status='overdue').aggregate(Sum('amount'))['amount__sum'] or 0
        
        message = f"""
📊 <b>ОТЧЕТ ПО СЧЕТАМ</b>

📅 <b>Период:</b> {date_from or 'Все время'} - {date_to or 'Сегодня'}
📋 <b>Фильтр статуса:</b> {dict(InvoiceRegistry.STATUS_CHOICES).get(status_filter, 'Все')}

📈 <b>Статистика:</b>
• Всего счетов: <b>{total_count}</b>
• Общая сумма: <b>{total_amount:,.2f} руб.</b>
• Оплачено: <b>{paid_amount:,.2f} руб.</b>
• Просрочено счетов: <b>{overdue_count}</b>
• Сумма просрочки: <b>{overdue_amount:,.2f} руб.</b>

📋 <b>Последние 10 счетов:</b>
"""
        
        for invoice in invoices.order_by('-invoice_date')[:10]:
            status_icon = {
                'paid': '✅',
                'overdue': '⏰',
                'sent': '📤',
                'created': '📝'
            }.get(invoice.status, '📄')
            
            message += f"\n{status_icon} <b>{invoice.invoice_number}</b>"
            message += f"\n   👤 {invoice.customer_name}"
            message += f"\n   💰 {invoice.amount:,.2f} руб."
            message += f"\n   📅 Срок: {invoice.due_date.strftime('%d.%m.%Y')}"
            
            if invoice.is_overdue():
                message += f" ⚠️ <b>Просрочен на {invoice.get_overdue_days()} дней</b>"
            
            message += f"\n   📧 {'✅' if invoice.email_sent else '❌'}"
            message += f" 📱 {'✅' if invoice.telegram_sent else '❌'}"
            message += "\n"
        
        message += f"\n⏰ <b>Время отчета:</b> {timezone.now().strftime('%d.%m.%Y %H:%M')}"
        
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': settings.TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            messages.success(request, 'Отчет успешно отправлен в Telegram')
            
            NotificationLog.objects.create(
                notification_type='telegram_sent',
                message=f'Отчет по счетам отправлен в Telegram. Фильтры: status={status_filter}, from={date_from}, to={date_to}',
                sent_to=f"Telegram: {settings.TELEGRAM_CHAT_ID}",
                success=True
            )
        else:
            messages.error(request, 'Ошибка отправки отчета')
    
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
    
    return redirect('invoice_registry')

@staff_member_required
def invoice_detail(request, invoice_id):
    """Детальная информация о счете"""
    invoice = get_object_or_404(InvoiceRegistry, id=invoice_id)
    order_items = invoice.order.orderitem_set.all()
    status_logs = OrderStatusLog.objects.filter(order=invoice.order).order_by('-changed_at')
    
    context = {
        'invoice': invoice,
        'order': invoice.order,
        'order_items': order_items,
        'status_logs': status_logs,
    }
    
    return render(request, 'main/invoice_detail.html', context)

@staff_member_required
def update_invoice_status(request, invoice_id):
    """Обновление статуса счета"""
    invoice = get_object_or_404(InvoiceRegistry, id=invoice_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if new_status in dict(InvoiceRegistry.STATUS_CHOICES):
            old_status = invoice.status
            invoice.status = new_status
            invoice.admin_notes = notes
            invoice.save()
            
            if new_status == 'paid' and invoice.order.status != 'paid':
                invoice.order.status = 'paid'
                invoice.order.paid_at = timezone.now()
                invoice.order.is_payment_finalized = True
                invoice.order.save()
            
            messages.success(request, f'Статус счета {invoice.invoice_number} обновлен')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'new_status': invoice.get_status_display(),
                    'status_class': new_status
                })
    
    return redirect('invoice_detail', invoice_id=invoice_id)

def turnkey_projects(request):
    return render(request, 'main/turnkey.html')