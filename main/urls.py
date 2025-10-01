# main/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('products/', views.products, name='products'),
    
    # Аутентификация
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='main/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    
    # Профиль
    path('profile/', views.profile, name='profile'),
    path('profile/address/delete/<int:address_id>/', views.delete_address, name='delete_address'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Корзина и заказы
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('orders/', views.orders_view, name='orders'),
    path('order/cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    
    # Оплата через ЮКассу
    path('payment/create/<int:order_id>/', views.create_payment, name='create_payment'),
    path('payment/success/<int:order_id>/', views.payment_success, name='payment_success'),
    path('webhook/yookassa/', views.yookassa_webhook, name='yookassa_webhook'),
    
    # API
    path('api/update-quantity/<int:product_id>/', views.update_quantity_ajax, name='update_quantity_ajax'),
]