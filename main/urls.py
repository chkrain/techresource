# main/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from django.http import HttpResponseNotFound
from django.urls import path, re_path
from django.contrib import admin
from . import views
from django.views.generic.base import RedirectView
from django.conf import settings
from django.views.generic import TemplateView
from main.sitemap import StaticViewSitemap
from django.contrib.sitemaps.views import sitemap

sitemaps = {
    'static' : StaticViewSitemap,
}

urlpatterns = [
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('yandex_8820f023c5e740e9.html', views.yandex_8820f023c5e740e9, name='yandex_8820f023c5e740e9'),

    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('contacts/', views.contacts, name='contacts'),
    path('privacy/', views.privacy_policy, name='privacy'),
    
    # Аутентификация и профиль
    path('register/', views.secure_register, name='register'),
    path('login/', views.secure_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/address/delete/<int:address_id>/', views.delete_address, name='delete_address'),
    path('change-password/', views.secure_change_password, name='change_password'),
    
    # Восстановление пароля (ваши новые пути)
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/verify/', views.verify_reset_code, name='verify_reset_code'),
    path('password-reset/set-password/', views.set_new_password, name='set_new_password'),
    
    # Подтверждение email
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),

    path('order/<int:order_id>/resend-invoice/', views.resend_invoice, name='resend_invoice'),
    
    # Товары
    path('products/', views.products, name='products'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/review/add/', views.add_review, name='add_review'),
    
    # Отзывы
    path('review/<int:review_id>/edit/', views.edit_review, name='edit_review'),
    path('review/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    
    # Корзина
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),

    # Анонимная корзина
    path('anonymous-cart/items/', views.anonymous_cart_items, name='anonymous_cart_items'),
    path('anonymous-cart/add/<int:product_id>/', views.anonymous_add_to_cart, name='anonymous_add_to_cart'),
    path('anonymous-cart/update/', views.anonymous_update_cart, name='anonymous_update_cart'),
    path('anonymous-cart/remove/', views.anonymous_remove_from_cart, name='anonymous_remove_from_cart'),
    path('anonymous-cart/create-order/', views.anonymous_create_order, name='anonymous_create_order'),
    path('anonymous-order/', views.anonymous_order_page, name='anonymous_order_page'),
    
    # Заказы
    path('orders/', views.orders_view, name='orders'),
    path('order/<int:order_id>/', views.order_details, name='order_details'),
    path('order/<int:order_id>/request-refund/', views.request_order_refund, name='request_order_refund'),
    path('order/<int:order_id>/timeline/', views.get_order_timeline, name='get_order_timeline'),
    path('reorder/<int:order_id>/', views.reorder_order, name='reorder_order'),
    path('orders/cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    
    # Избранное
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('wishlist/to-cart/<int:product_id>/', views.wishlist_to_cart, name='wishlist_to_cart'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/clear/', views.clear_wishlist, name='clear_wishlist'),
    
    # Услуги
    path('services/', views.services_main, name='services'),  # Главная страница услуг
    # Статические страницы услуг
    path('services/design/', views.service_design, name='service_design'),
    path('services/electrical/', views.service_electrical, name='service_electrical'),
    path('services/software/', views.service_software, name='service_software'),
    path('services/equipment/', views.service_equipment, name='service_equipment'),
    path('services/support/', views.service_support, name='service_support'),
    path('services/maintenance/', views.service_maintenance, name='service_maintenance'),
    # Динамические страницы услуг
    path('services/dynamic/<slug:service_slug>/', views.dynamic_service_page, name='dynamic_service_page'),
    path('services/dynamic/<slug:service_slug>/<slug:sub_slug>/', views.dynamic_service_page, name='dynamic_sub_service'),
    path('services/dynamic/<slug:service_slug>/<slug:sub_slug>/instructions/<slug:instruction_slug>/', 
         views.dynamic_service_page, name='dynamic_instruction_page'),
    
    # Инструкции
    path('instructions/altyshevo/', views.altyshevo_instruction, name='altyshevo_instruction'),
    
    # Поддержка
    path('support/', views.support_view, name='support'),
    path('contact/submit/', views.contact_form_submit, name='contact_submit'),
    
    path('profile/preview/', views.profile_preview, name='profile_preview'),
    path('profile/<str:slug_or_id>/', views.public_profile, name='public_profile'),
    path('profile/update-field/', views.update_profile_field, name='update_profile_field'),
    path('profile/upload-avatar/', views.upload_avatar, name='upload_avatar'),
    path('profile/card/<int:user_id>/', views.profile_card, name='profile_card'),
    # Админка
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/order/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('moderate-review/<int:review_id>/', views.moderate_review, name='moderate_review'),
    path('moderate-comment/<int:comment_id>/', views.moderate_comment, name='moderate_comment'),
    path('moderate-all-comments/', views.moderate_all_comments, name='moderate_all_comments'),
    path('admin/profile/manage/<int:user_id>/', views.admin_profile_manage, name='admin_profile_manage'),
    
    # API
    path('api/search-suggestions/', views.search_suggestions, name='search_suggestions'),
    path('api/price-range/', views.get_price_range, name='get_price_range'),
    path('api/update-quantity/<int:product_id>/', views.update_quantity_ajax, name='update_quantity_ajax'),
    
    # Favicon
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'images/favicon/favicon.ico')),
    
    # Для .well-known
    re_path(r'^\.well-known/.*$', lambda request: HttpResponseNotFound()),

    path('manifest.json', TemplateView.as_view(template_name='manifest.json',content_type='application/json'), name='manifest'),
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
]