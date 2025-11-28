# main/context_processors.py
from .models import Wishlist, Cart

def base_context(request):
    """Добавляем счетчики в контекст всех страниц"""
    context = {
        'wishlist_count': 0,
        'cart_count': 0
    }
    
    try:
        # Безопасная проверка аутентификации пользователя
        user = getattr(request, 'user', None)
        if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
            # Счетчик избранного
            wishlist, created = Wishlist.objects.get_or_create(user=user)
            context['wishlist_count'] = wishlist.get_items_count()
            
            # Счетчик корзины
            cart, created = Cart.objects.get_or_create(user=user)
            context['cart_count'] = cart.get_items_count()
            
    except Exception as e:
        # Логируем ошибку но не падаем
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in base_context processor: {e}")
    
    return context