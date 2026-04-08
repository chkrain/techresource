# main/context_processors.py
from .models import Wishlist, Cart
from django.conf import settings

def base_context(request):
    """Добавляем счетчики в контекст всех страниц"""
    context = {
        'wishlist_count': 0,
        'cart_count': 0
    }

    context.update({
        'company_email': getattr(settings, 'COMPANY_EMAIL', 'techreru@yahoo.com'),
        'company_phone': getattr(settings, 'COMPANY_NUMBER', '8 (937) 524-68-88'),
        'company_name': getattr(settings, 'COMPANY_NAME', 'Техресурс'),
        'company_address': getattr(settings, 'COMPANY_ADDRESS', 'Казань, ул. Техническая, 52'),
        'company_work_hours': getattr(settings, 'COMPANY_WORK_HOURS', 'Пн-Пт: 8:00-17:00'),
        'static_version': getattr(settings, 'STATIC_VERSION', '1.0'),
    })
    
    try:
        user = getattr(request, 'user', None)
        if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
            wishlist, created = Wishlist.objects.get_or_create(user=user)
            context['wishlist_count'] = wishlist.get_items_count()
            
            cart, created = Cart.objects.get_or_create(user=user)
            context['cart_count'] = cart.get_items_count()
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in base_context processor: {e}")
    
    return context