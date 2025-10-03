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
    path('register/', views.secure_register, name='register'),
    path('login/', views.secure_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),

    path('debug/codes/', views.debug_codes, name='debug_codes'), #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    path('contact/submit/', views.contact_form_submit, name='contact_submit'),


    # Восстановление пароля
    path('password-reset/', views.secure_password_reset, name='password_reset'),
    path('password-reset-confirm/<str:token>/', views.secure_password_reset_confirm, name='password_reset_confirm'),

    # Смена пароля
    path('change-password/', views.secure_change_password, name='change_password'),

    # Подтверждение email
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    
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
    
    # Политика конфиденциальности
    path('privacy/', views.privacy_policy, name='privacy'),
]