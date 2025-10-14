# main/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from django.http import HttpResponseNotFound
from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('products/', views.products, name='products'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/review/add/', views.add_review, name='add_review'),
    path('review/<int:review_id>/edit/', views.edit_review, name='edit_review'),
    path('review/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    path('api/search-suggestions/', views.search_suggestions, name='search_suggestions'),
    path('api/price-range/', views.get_price_range, name='get_price_range'),
    
    # Аутентификация
    path('register/', views.secure_register, name='register'),
    path('login/', views.secure_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),

    path('debug/codes/', views.debug_codes, name='debug_codes'), #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    path('contact/submit/', views.contact_form_submit, name='contact_submit'),

    # Страницы услуг
    path('services/design/', views.service_design, name='service_design'),
    path('services/electrical/', views.service_electrical, name='service_electrical'),
    path('services/software/', views.service_software, name='service_software'),
    path('services/equipment/', views.service_equipment, name='service_equipment'),
    path('services/support/', views.service_support, name='service_support'),
    path('services/maintenance/', views.service_maintenance, name='service_maintenance'),

    # Восстановление пароля
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='main/password_reset_form.html',
             email_template_name='main/password_reset_email.html',
             subject_template_name='main/password_reset_subject.txt',
             success_url='/password-reset/done/'
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='main/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='main/password_reset_confirm.html',
             success_url='/password-reset/complete/'
         ), 
         name='password_reset_confirm'),
    path('password-reset/complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='main/password_reset_complete.html'
         ), 
         name='password_reset_complete'),

    # Смена пароля
    path('change-password/', views.secure_change_password, name='change_password'),

    # Подтверждение email
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    
    # Профиль
    path('profile/', views.profile, name='profile'),
    path('profile/address/delete/<int:address_id>/', views.delete_address, name='delete_address'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('moderate-review/<int:review_id>/', views.moderate_review, name='moderate_review'),
    
    
    # Корзина и заказы
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('orders/', views.orders_view, name='orders'),
    path('order/cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('order/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('order/<int:order_id>/timeline/', views.get_order_timeline, name='get_order_timeline'),
    path('order/<int:order_id>/request-refund/', views.request_order_refund, name='request_order_refund'),
    path('order/update-status/', views.update_order_status, name='update_order_status_post'),
    path('order/<int:order_id>/reorder/', views.reorder_order, name='reorder_order'),
    path('order/<int:order_id>/details/', views.order_details, name='order_details'),
    

    # Избранное
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('wishlist/to-cart/<int:product_id>/', views.wishlist_to_cart, name='wishlist_to_cart'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/clear/', views.clear_wishlist, name='clear_wishlist'),

    path('test-email/', views.test_email_sending, name='test_email'),

    # Оплата через ЮКассу
    path('payment/create/<int:order_id>/', views.create_payment, name='create_payment'),
    path('payment/success/<int:order_id>/', views.payment_success, name='payment_success'),
    path('webhook/yookassa/', views.yookassa_webhook, name='yookassa_webhook'),
    path('payment/failed/<int:order_id>/', views.payment_failed, name='payment_failed'),
    path('payment/retry/<int:order_id>/', views.retry_payment, name='retry_payment'),
    path('payment/update-method/<int:order_id>/', views.update_order_payment_method, name='update_order_payment_method'),
    
    path('contacts/', views.contacts, name='contacts'),

    # API
    path('api/update-quantity/<int:product_id>/', views.update_quantity_ajax, name='update_quantity_ajax'),
    
    # Политика конфиденциальности
    path('privacy/', views.privacy_policy, name='privacy'),

    re_path(r'^\.well-known/.*$', lambda request: HttpResponseNotFound()),
]