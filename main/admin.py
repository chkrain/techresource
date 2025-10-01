# main/admin.py
from django.contrib import admin
from .models import Product, Cart, CartItem, Order, OrderItem, UserProfile, Address, NotificationLog

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price', 'get_total_price']

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

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'get_total_price']
    list_filter = ['cart__user']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'customer_name', 'total_price', 'status', 'payment_method', 'created_at', 'paid_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['customer_name', 'customer_phone', 'customer_email', 'id']
    list_editable = ['status']
    readonly_fields = ['created_at', 'paid_at', 'cancelled_at']
    inlines = [OrderItemInline, NotificationLogInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'status', 'total_price', 'payment_method', 'payment_id')
        }),
        ('Данные клиента', {
            'fields': ('customer_name', 'customer_phone', 'customer_email', 'delivery_address')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'paid_at', 'cancelled_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'notification_type', 'success', 'created_at']
    list_filter = ['notification_type', 'success', 'created_at']
    search_fields = ['order__id', 'message']
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price', 'get_total_price']
    list_filter = ['order__status']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'company', 'position']
    search_fields = ['user__username', 'phone', 'company']

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'city', 'address', 'is_default']
    list_filter = ['city', 'is_default']
    search_fields = ['user__username', 'city', 'address']