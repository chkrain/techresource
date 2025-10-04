# main/admin.py
from django.contrib import admin
from .models import Product, Cart, CartItem, Order, OrderItem, UserProfile, Address, NotificationLog, OrderStatusLog

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price', 'get_total_price']
    
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

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'article', 'price', 'quantity', 'category', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'article', 'description']
    list_editable = ['price', 'quantity', 'is_active']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'get_total_price']
    list_filter = ['created_at']
    
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

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_user', 'get_customer_name', 'get_total_price', 'get_status_display', 'get_payment_method_display', 'get_created_at', 'get_paid_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['customer_name', 'customer_phone', 'customer_email', 'id']
    readonly_fields = ['get_created_at', 'get_paid_at', 'get_cancelled_at', 'status_changed_at']
    inlines = [OrderItemInline, OrderStatusLogInline, NotificationLogInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'status', 'total_price', 'payment_method', 'payment_id')
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
    
    # Методы для list_display
    def get_user(self, obj):
        return obj.user.username
    get_user.short_description = 'Пользователь'
    
    def get_customer_name(self, obj):
        return obj.customer_name
    get_customer_name.short_description = 'Имя клиента'
    
    def get_total_price(self, obj):
        return obj.total_price
    get_total_price.short_description = 'Общая сумма'
    
    def get_status_display(self, obj):
        return obj.get_status_display()
    get_status_display.short_description = 'Статус'
    
    def get_payment_method_display(self, obj):
        return obj.get_payment_method_display()
    get_payment_method_display.short_description = 'Способ оплаты'
    
    def get_created_at(self, obj):
        return obj.created_at
    get_created_at.short_description = 'Дата создания'
    
    def get_paid_at(self, obj):
        return obj.paid_at
    get_paid_at.short_description = 'Дата оплаты'
    
    def get_cancelled_at(self, obj):
        return obj.cancelled_at
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

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['get_order_id', 'product', 'quantity', 'price', 'get_total_price']
    list_filter = ['order__status']
    
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
    list_display = ['user', 'phone', 'company', 'position']
    search_fields = ['user__username', 'phone', 'company']

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'city', 'address', 'is_default']
    list_filter = ['city', 'is_default']
    search_fields = ['user__username', 'city', 'address']