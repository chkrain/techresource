# main/context_processors.py
from .models import Wishlist, Cart

def base_context(request):
    """Добавляем счетчики в контекст всех страниц"""
    context = {}
    
    if request.user.is_authenticated:
        try:
            # Счетчик избранного
            wishlist, created = Wishlist.objects.get_or_create(user=request.user)
            context['wishlist_count'] = wishlist.get_items_count()
        except Exception as e:
            print(f"Ошибка в контекстном процессоре (wishlist): {e}")
            context['wishlist_count'] = 0
        
        try:
            # Счетчик корзины
            cart, created = Cart.objects.get_or_create(user=request.user)
            context['cart_count'] = cart.get_items_count()
        except Exception as e:
            print(f"Ошибка в контекстном процессоре (cart): {e}")
            context['cart_count'] = 0
    else:
        context['wishlist_count'] = 0
        context['cart_count'] = 0
    
    return context