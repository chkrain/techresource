# main/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.contrib import messages
import logging
from django.utils.html import format_html


from .models import (
    Product, Cart, CartItem, Order, OrderItem, UserProfile, Address, 
    NotificationLog, OrderStatusLog, ProductReview, ProductImage,
    SecurityLog, LoginAttempt, PaymentAuditLog, Admin2FA,
    FraudDetectionLog, RateLimitLog, CSPViolationReport, Wishlist, WishlistItem,
    SupportTicket, SupportAttachment, ServicePage
)

logger = logging.getLogger('django.security')


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Профиль'

class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'last_login', 'date_joined']
    list_filter = ['is_staff', 'is_active', 'is_superuser', 'last_login', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    readonly_fields = ['last_login', 'date_joined']
    actions = ['deactivate_users', 'activate_users']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    def deactivate_users(self, request, queryset):
        """Безопасное отключение пользователей"""
        if request.user.is_superuser:
            updated = queryset.update(is_active=False)
            self.message_user(request, f'{updated} пользователей деактивировано')
            
            logger.warning(
                f"Admin {request.user} deactivated {updated} users: {list(queryset.values_list('username', flat=True))}"
            )
        else:
            self.message_user(request, 'Недостаточно прав для выполнения этой операции', level=messages.ERROR)
    deactivate_users.short_description = "Деактивировать выбранных пользователей"
    
    def activate_users(self, request, queryset):
        """Активация пользователей"""
        if request.user.is_superuser:
            updated = queryset.update(is_active=True)
            self.message_user(request, f'{updated} пользователей активировано')
    activate_users.short_description = "Активировать выбранных пользователей"
    
    def get_queryset(self, request):
        """Ограничение видимости для не-superuser админов"""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(is_superuser=False)
        return qs
    
    def has_delete_permission(self, request, obj=None):
        """Только superuser могут удалять пользователей"""
        return request.user.is_superuser
    
    def save_model(self, request, obj, form, change):
        """Логирование изменений пользователей"""
        if change:
            logger.info(f"Admin {request.user} modified user {obj.username}")
        super().save_model(request, obj, form, change)

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Admin2FA)
class Admin2FAAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_enabled', 'last_used', 'created_at']
    list_filter = ['is_enabled', 'last_used', 'created_at']
    readonly_fields = ['secret_key', 'backup_codes', 'last_used', 'created_at']
    search_fields = ['user__username']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'ip_address', 'success', 'risk_level', 'timestamp']
    list_filter = ['action', 'success', 'risk_level', 'timestamp']
    search_fields = ['user__username', 'ip_address', 'action']
    readonly_fields = ['user', 'action', 'ip_address', 'user_agent', 'success', 'timestamp', 'details', 'risk_level']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(PaymentAuditLog)
class PaymentAuditLogAdmin(admin.ModelAdmin):
    list_display = ['order', 'action', 'user', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['order__id', 'user__username', 'ip_address']
    readonly_fields = ['order', 'action', 'user', 'ip_address', 'user_agent', 'details', 'created_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(RateLimitLog)
class RateLimitLogAdmin(admin.ModelAdmin):
    list_display = ['key', 'ip_address', 'user', 'action', 'attempts', 'window_start']
    list_filter = ['action', 'window_start']
    search_fields = ['key', 'ip_address', 'user__username']
    readonly_fields = ['key', 'ip_address', 'user', 'action', 'attempts', 'window_start', 'window_end', 'blocked_until']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(FraudDetectionLog)
class FraudDetectionLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'order', 'ip_address', 'severity', 'detected_at', 'resolved']
    list_filter = ['severity', 'resolved', 'detected_at']
    search_fields = ['user__username', 'order__id', 'ip_address', 'description']
    readonly_fields = ['user', 'order', 'ip_address', 'severity', 'description', 'reasons', 'detected_at']
    actions = ['mark_as_resolved']
    
    def mark_as_resolved(self, request, queryset):
        """Пометить как решенные"""
        updated = queryset.update(resolved=True, resolved_at=timezone.now(), resolved_by=request.user)
        self.message_user(request, f'{updated} случаев помечено как решенные')
    mark_as_resolved.short_description = "Пометить как решенные"
    
    def has_add_permission(self, request):
        return False

@admin.register(CSPViolationReport)
class CSPViolationReportAdmin(admin.ModelAdmin):
    list_display = ['violated_directive', 'document_uri', 'ip_address', 'created_at']
    list_filter = ['violated_directive', 'created_at']
    search_fields = ['document_uri', 'violated_directive', 'ip_address']
    readonly_fields = ['document_uri', 'violated_directive', 'effective_directive', 'original_policy', 
                      'blocked_uri', 'source_file', 'line_number', 'column_number', 'user_agent', 
                      'ip_address', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ['username', 'ip_address', 'success', 'timestamp']
    list_filter = ['success', 'timestamp']
    search_fields = ['username', 'ip_address']
    readonly_fields = ['username', 'ip_address', 'user_agent', 'success', 'timestamp']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price', 'get_total_price']
    can_delete = False
    
    def get_total_price(self, obj):
        return obj.get_total_price()
    get_total_price.short_description = 'Общая стоимость'

class OrderStatusLogInline(admin.TabularInline):
    model = OrderStatusLog
    extra = 0
    readonly_fields = ['old_status', 'new_status', 'changed_by', 'changed_at', 'notes']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

class NotificationLogInline(admin.TabularInline):
    model = NotificationLog
    extra = 0
    readonly_fields = ['notification_type', 'message', 'sent_to', 'created_at', 'success']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'order', 'is_main']
    readonly_fields = ['preview']
    
    def preview(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" style="max-height: 100px;" />')
        return "Нет изображения"
    preview.short_description = "Предпросмотр"

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['article', 'name', 'category', 'price', 'quantity', 'is_active', 'get_article_date']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'article', 'description']
    list_editable = ['price', 'quantity', 'is_active']
    readonly_fields = ['article', 'slug', 'seo_title', 'seo_description', 'seo_keywords', 'created_at', 'updated_at', 'get_article_date']
    inlines = [ProductImageInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'category', 'brand', 'description', 'article', 'get_article_date', 'slug'),
            'description': 'Обязательные поля: название, категория, цена и количество. Бренд и описание - рекомендуются.'
        }),
        ('Цена и наличие', {
            'fields': ('price', 'quantity', 'is_active'),
            'description': 'Цена в рублях. Количество должно быть неотрицательным.'
        }),
        ('Технические характеристики', {
            'fields': ('material', 'weight', 'dimensions', 'warranty', 'specifications'),
            'classes': ('collapse',),
            'description': '''
                <strong>Инструкция по заполнению:</strong><br>
                1. <strong>Материал</strong> - основной материал изделия (пластик, металл и т.д.)<br>
                2. <strong>Вес</strong> - в килограммах, с точностью до сотых (2.50)<br>
                3. <strong>Габариты</strong> - формат: Длина×Ширина×Высота в см (10×20×5)<br>
                4. <strong>Гарантия</strong> - срок в месяцах, по умолчанию 12<br>
                5. <strong>Характеристики (JSON)</strong> - дополнительные параметры в формате ключ: значение<br>
                &nbsp;&nbsp;&nbsp;Пример: {"Мощность": "100W", "Напряжение": "220V", "Цвет": "черный"}<br>
                <em>Все эти поля необязательны, но помогают покупателям найти товар</em>
            '''
        }),
        ('SEO настройки (автозаполняются)', {
            'fields': ('seo_title', 'seo_description', 'seo_keywords'),
            'classes': ('collapse',),
            'description': 'Эти поля заполняются автоматически на основе названия и описания.'
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_fieldsets(self, request, obj=None):
        """Показываем разные наборы полей для создания и редактирования"""
        if obj is None:
            return (
                ('Основная информация*', {
                    'fields': ('name', 'category', 'brand'),
                    'description': 'Заполните эти три поля. Остальные заполнятся автоматически.'
                }),
                ('Описание (рекомендуется)', {
                    'fields': ('description',),
                    'classes': ('collapse',)
                }),
                ('Цена и наличие*', {
                    'fields': ('price', 'quantity', 'is_active')
                }),
            )
        else:
            return super().get_fieldsets(request, obj)
    
    def get_article_date(self, obj):
        """Отображение даты из артикула в списке"""
        return obj.get_article_date()
    get_article_date.short_description = 'Дата добавления'
    get_article_date.admin_order_field = 'created_at'

    def get_readonly_fields(self, request, obj=None):
        if obj:  
            return ['article', 'slug', 'seo_title', 'seo_description', 'seo_keywords', 'created_at', 'updated_at', 'get_article_date']
        else:  
            return ['article', 'slug', 'seo_title', 'seo_description', 'seo_keywords', 'created_at', 'updated_at', 'get_article_date']

    def save_model(self, request, obj, form, change):
        """Логирование изменений товаров"""
        if not change:  
            logger.info(f"Admin {request.user} создал товар '{obj.name}' с артикулом {obj.article}")
        else:
            logger.info(f"Admin {request.user} изменил товар '{obj.name}' (арт: {obj.article})")
        
        super().save_model(request, obj, form, change)

    def add_view(self, request, form_url='', extra_context=None):
        """Кастомное отображение для добавления товара"""
        extra_context = extra_context or {}
        extra_context['show_save_and_add_another'] = True
        extra_context['show_save_and_continue'] = False
        return super().add_view(request, form_url, extra_context)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_user', 'get_customer_name', 'get_total_price', 'get_status_display', 'get_payment_method_display', 'get_created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['customer_name', 'customer_phone', 'customer_email', 'id']
    readonly_fields = ['get_created_at', 'get_paid_at', 'get_cancelled_at', 'status_changed_at']
    inlines = [OrderItemInline, OrderStatusLogInline, NotificationLogInline]
    actions = ['export_orders', 'mark_as_shipped']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'status', 'total_price', 'payment_method')
        }),
        ('Данные клиента', {
            'fields': ('customer_name', 'customer_phone', 'customer_email', 'delivery_address')
        }),
        ('Информация о доставке', {
            'fields': ('tracking_number', 'shipping_company', 'estimated_delivery')
        }),
        ('Временные метки', {
            'fields': ('get_created_at', 'get_paid_at', 'get_cancelled_at', 'status_changed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Ограничение видимости заказов для не-superuser админов"""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Обычные админы видят только последние 1000 заказов
            qs = qs.order_by('-created_at')[:1000]
        return qs
    
    def export_orders(self, request, queryset):
        """Экспорт заказов (только для superuser)"""
        if not request.user.is_superuser:
            self.message_user(request, 'Недостаточно прав для экспорта', level=messages.ERROR)
            return
        
        # Здесь может быть логика экспорта
        self.message_user(request, f'Экспортировано {queryset.count()} заказов')
    export_orders.short_description = "Экспортировать выбранные заказы"
    
    def mark_as_shipped(self, request, queryset):
        """Пометить как отправленные"""
        updated = queryset.update(status='shipped')
        self.message_user(request, f'{updated} заказов помечены как отправленные')
    mark_as_shipped.short_description = "Пометить как отправленные"
    
    # Методы для list_display
    def get_user(self, obj):
        return obj.user.username if obj.user else 'Гость'
    get_user.short_description = 'Пользователь'
    
    def get_customer_name(self, obj):
        return obj.customer_name
    get_customer_name.short_description = 'Имя клиента'
    
    def get_total_price(self, obj):
        return f"{obj.total_price} руб."
    get_total_price.short_description = 'Общая сумма'
    
    def get_status_display(self, obj):
        return obj.get_status_display()
    get_status_display.short_description = 'Статус'
    
    def get_payment_method_display(self, obj):
        return obj.get_payment_method_display()
    get_payment_method_display.short_description = 'Способ оплаты'
    
    def get_created_at(self, obj):
        return obj.created_at.strftime('%d.%m.%Y %H:%M')
    get_created_at.short_description = 'Дата создания'
    
    def get_paid_at(self, obj):
        return obj.paid_at.strftime('%d.%m.%Y %H:%M') if obj.paid_at else '-'
    get_paid_at.short_description = 'Дата оплаты'
    
    def get_cancelled_at(self, obj):
        return obj.cancelled_at.strftime('%d.%m.%Y %H:%M') if obj.cancelled_at else '-'
    get_cancelled_at.short_description = 'Дата отмены'

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_order_id', 'notification_type', 'success', 'created_at']
    list_filter = ['notification_type', 'success', 'created_at']
    search_fields = ['order__id', 'message']
    readonly_fields = ['created_at']
    
    def get_order_id(self, obj):
        return obj.order.id if obj.order else '-'
    get_order_id.short_description = 'ID заказа'
    
    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_approved', 'is_moderated', 'created_at']
    list_filter = ['rating', 'is_approved', 'is_moderated', 'created_at']
    search_fields = ['product__name', 'user__username', 'comment']
    list_editable = ['is_approved', 'is_moderated']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['approve_reviews', 'reject_reviews', 'bulk_delete_reviews']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('product', 'user', 'rating', 'comment')
        }),
        ('Модерация', {
            'fields': ('is_approved', 'is_moderated', 'created_at', 'updated_at')
        }),
    )
    
    def approve_reviews(self, request, queryset):
        """Действие для одобрения отзывов"""
        updated = queryset.update(is_approved=True, is_moderated=True)
        self.message_user(request, f'{updated} отзывов одобрено.')
        
        # Логирование
        logger.info(f"Admin {request.user} approved {updated} reviews")
    approve_reviews.short_description = "Одобрить выбранные отзывы"
    
    def reject_reviews(self, request, queryset):
        """Действие для отклонения отзывов"""
        updated = queryset.update(is_approved=False, is_moderated=True)
        self.message_user(request, f'{updated} отзывов отклонено.')
        
        # Логирование
        logger.info(f"Admin {request.user} rejected {updated} reviews")
    reject_reviews.short_description = "Отклонить выбранные отзывы"
    
    def bulk_delete_reviews(self, request, queryset):
        """Массовое удаление отзывов (только для superuser)"""
        if not request.user.is_superuser:
            self.message_user(request, 'Недостаточно прав для массового удаления', level=messages.ERROR)
            return
        
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} отзывов удалено.')
        
        # Логирование
        logger.warning(f"Admin {request.user} bulk deleted {count} reviews")
    bulk_delete_reviews.short_description = "Массовое удаление отзывов"

# Остальные модели с базовой безопасностью
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'get_total_price']
    list_filter = ['created_at']
    readonly_fields = ['created_at']
    
    def get_total_price(self, obj):
        return obj.get_total_price()
    get_total_price.short_description = 'Общая стоимость'

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'get_total_price']
    list_filter = ['cart__user']
    
    def get_total_price(self, obj):
        return obj.get_total_price()
    get_total_price.short_description = 'Общая стоимость'

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['get_order_id', 'product', 'quantity', 'price', 'get_total_price']
    list_filter = ['order__status']
    readonly_fields = ['price']
    
    def get_order_id(self, obj):
        return obj.order.id
    get_order_id.short_description = 'ID заказа'
    
    def get_total_price(self, obj):
        return obj.get_total_price()
    get_total_price.short_description = 'Общая стоимость'

@admin.register(OrderStatusLog)
class OrderStatusLogAdmin(admin.ModelAdmin):
    list_display = ['order', 'old_status', 'new_status', 'changed_by', 'changed_at']
    list_filter = ['changed_at', 'old_status', 'new_status']
    readonly_fields = ['changed_at']
    
    def has_add_permission(self, request):
        return False

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'company', 'position', 'email_verified']
    search_fields = ['user__username', 'phone', 'company']
    readonly_fields = ['user', 'email_verified', 'verification_token_created']

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'city', 'address', 'is_default']
    list_filter = ['city', 'is_default']
    search_fields = ['user__username', 'city', 'address']

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'get_items_count']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_items_count(self, obj):
        return obj.get_items_count()
    get_items_count.short_description = 'Количество товаров'

@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ['wishlist', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['wishlist__user__username', 'product__name']

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'subject', 'priority', 'status', 'created_at']
    list_filter = ['priority', 'status', 'created_at']
    search_fields = ['subject', 'user__username', 'description']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['mark_as_resolved', 'mark_as_in_progress']
    
    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(status='resolved')
        self.message_user(request, f'{updated} заявок помечено как решенные')
    mark_as_resolved.short_description = "Пометить как решенные"
    
    def mark_as_in_progress(self, request, queryset):
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'{updated} заявок помечено как в обработке')
    mark_as_in_progress.short_description = "Пометить как в обработке"

@admin.register(SupportAttachment)
class SupportAttachmentAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'file_name', 'file_size', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['ticket__subject', 'file_name']
    readonly_fields = ['uploaded_at']

@admin.register(ServicePage)
class ServicePageAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'page_type', 'static_service', 'parent', 'order', 'is_active', 'show_in_navigation']
    list_filter = ['page_type', 'static_service', 'is_active', 'show_in_navigation', 'created_at']
    list_editable = ['order', 'is_active', 'show_in_navigation']
    search_fields = ['title', 'slug', 'content']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'slug', 'page_type', 'static_service', 'parent', 'order')
        }),
        ('Герой страницы', {
            'fields': ('hero_title', 'hero_subtitle', 'hero_image'),
            'classes': ('collapse',)
        }),
        ('Контент', {
            'fields': ('content', 'features_text'),
            'description': 'В поле "Особенности" вводите каждую особенность с новой строки. Формат: Заголовок|Описание'
        }),
        ('Настройки', {
            'fields': ('meta_description', 'is_active', 'show_in_navigation')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            kwargs["queryset"] = ServicePage.objects.filter(
                page_type__in=['main_service', 'sub_service']
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)