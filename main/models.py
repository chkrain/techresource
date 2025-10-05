# main/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import secrets
import hashlib
import time
from datetime import timedelta
from django.conf import settings

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE) 
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Телефон')
    company = models.CharField(max_length=100, blank=True, verbose_name='Компания')
    position = models.CharField(max_length=100, blank=True, verbose_name='Должность')
    date_of_birth = models.DateField(blank=True, null=True, verbose_name='Дата рождения')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Аватар')
    
    # Поля для восстановления пароля
    phone_verified = models.BooleanField(default=False, verbose_name='Телефон подтвержден')
    sms_code = models.CharField(max_length=6, blank=True, null=True, verbose_name='Код из SMS')
    sms_code_expires = models.DateTimeField(blank=True, null=True, verbose_name='Код действует до')
    reset_token = models.CharField(max_length=100, blank=True, null=True, verbose_name='Токен сброса')
    reset_token_expires = models.DateTimeField(blank=True, null=True, verbose_name='Токен действует до')
    
    def __str__(self):
        return f"Профиль {self.user.username}"
    
    def age(self):
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None
    
    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    title = models.CharField(max_length=100, verbose_name="Название адреса", default="Основной")
    full_name = models.CharField(max_length=200, verbose_name="ФИО")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    address = models.TextField(verbose_name="Адрес")
    city = models.CharField(max_length=100, verbose_name="Город")
    postal_code = models.CharField(max_length=20, verbose_name="Почтовый индекс")
    is_default = models.BooleanField(default=False, verbose_name="Адрес по умолчанию")
    
    def __str__(self):
        return f"{self.title} - {self.city}"
    
    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Адрес"
        verbose_name_plural = "Адреса"

# models.py - добавить в модель Product
class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    description = models.TextField(verbose_name="Описание", blank=True)
    quantity = models.IntegerField(default=0, verbose_name="Остаток")
    category = models.CharField(max_length=100, verbose_name="Категория", blank=True)
    article = models.CharField(max_length=50, verbose_name="Артикул", blank=True)
    image = models.ImageField(upload_to='products/', verbose_name="Изображение", blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="Активный")
    
    brand = models.CharField(max_length=100, verbose_name="Бренд", blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name="Рейтинг")
    popularity = models.IntegerField(default=0, verbose_name="Популярность")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="Вес")
    dimensions = models.CharField(max_length=50, blank=True, verbose_name="Габариты")
    material = models.CharField(max_length=100, blank=True, verbose_name="Материал")
    warranty = models.IntegerField(default=12, verbose_name="Гарантия (мес)")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['name']

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    def __str__(self):
        return f"Корзина {self.user.username}"
    
    def get_total_price(self):
        return sum(item.get_total_price() for item in self.cartitem_set.all())
    
    def get_items_count(self):
        """Возвращает общее количество товаров в корзине"""
        return sum(item.quantity for item in self.cartitem_set.all())
    
    def get_total_quantity(self):
        """Возвращает количество позиций (разных товаров) в корзине"""
        return self.cartitem_set.count()
    
    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, verbose_name="Корзина")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def get_total_price(self):
        return self.product.price * self.quantity
    
    class Meta:
        verbose_name = "Элемент корзины"
        verbose_name_plural = "Элементы корзины"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачен'),
        ('processing', 'В обработке'),
        ('assembling', 'Собирается'),
        ('ready_for_shipping', 'Готов к отправке'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
        ('refunded', 'Возврат'),
    ]
    
    PAYMENT_METHODS = [
        ('card', 'Банковская карта'),
        ('invoice', 'По счету'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Общая сумма")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='card', verbose_name="Способ оплаты")
    payment_id = models.CharField(max_length=100, blank=True, verbose_name="ID платежа")
    
    # Данные доставки
    customer_name = models.CharField(max_length=100, verbose_name="Имя клиента")
    customer_phone = models.CharField(max_length=20, verbose_name="Телефон")
    customer_email = models.EmailField(verbose_name="Email")
    delivery_address = models.TextField(verbose_name="Адрес доставки")
    
    # Новые поля для отслеживания
    status_changed_at = models.DateTimeField(auto_now=True, verbose_name="Время изменения статуса")  # Изменено на auto_now
    tracking_number = models.CharField(max_length=100, blank=True, verbose_name="Трек-номер")
    shipping_company = models.CharField(max_length=100, blank=True, verbose_name="Служба доставки")
    estimated_delivery = models.DateField(null=True, blank=True, verbose_name="Примерная дата доставки")
    
    # Таймстампы
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата оплаты")
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата отмены")
    
    def __str__(self):
        return f"Заказ #{self.id} - {self.customer_name}"
    
    def can_be_cancelled(self):
        """Можно отменить заказ в течение 10 минут после оплаты"""
        from django.utils import timezone
        if self.status == 'paid' and self.paid_at:
            return (timezone.now() - self.paid_at).total_seconds() < 3600  # час
        return False
    
    def get_status_timeline(self):
        """Возвращает временную шкалу статусов"""
        return {
            'paid': {'title': 'Оплата получена', 'description': 'Заказ подтвержден', 'icon': '💰'},
            'processing': {'title': 'Обработка заказа', 'description': 'Проверка деталей', 'icon': '📋'},
            'assembling': {'title': 'Сборка заказа', 'description': 'Собираем ваш заказ', 'icon': '🛠️'},
            'ready_for_shipping': {'title': 'Готов к отправке', 'description': 'Заказ упакован', 'icon': '📦'},
            'shipped': {'title': 'Отправлен', 'description': 'Передан в службу доставки', 'icon': '🚚'},
            'delivered': {'title': 'Доставлен', 'description': 'Товар у вас', 'icon': '🏠'},
            'completed': {'title': 'Завершен', 'description': 'Заказ выполнен', 'icon': '✅'}
        }
    
    def get_current_timeline(self):
        """Возвращает текущий прогресс по временной шкале"""
        timeline = self.get_status_timeline()
        status_flow = ['paid', 'processing', 'assembling', 'ready_for_shipping', 'shipped', 'delivered', 'completed']
        
        try:
            current_index = status_flow.index(self.status) if self.status in status_flow else -1
        except ValueError:
            current_index = -1
            
        result = {}
        
        for status_key, status_info in timeline.items():
            try:
                status_index = status_flow.index(status_key)
                is_completed = status_index <= current_index
                is_current = status_index == current_index
                
                result[status_key] = {
                    **status_info,
                    'completed': is_completed,
                    'current': is_current,
                    'order': status_index + 1
                }
            except ValueError:
                continue
        
        return result
    
    def save(self, *args, **kwargs):
        """Автоматическое обновление status_changed_at при изменении статуса"""
        if self.pk:
            old_status = Order.objects.get(pk=self.pk).status
            if old_status != self.status:
                self.status_changed_at = timezone.now()
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

class OrderStatusLog(models.Model):
    """Лог изменений статуса заказа"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="Заказ")
    old_status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES, verbose_name="Предыдущий статус")
    new_status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES, verbose_name="Новый статус")
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Изменил")
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="Время изменения")
    notes = models.TextField(blank=True, verbose_name="Примечания")
    
    def __str__(self):
        return f"Лог #{self.id} для заказа #{self.order.id}"
    
    class Meta:
        verbose_name = "Лог статуса заказа"
        verbose_name_plural = "Логи статусов заказов"
        ordering = ['-changed_at']

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="Заказ")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def get_total_price(self):
        if self.price is not None and self.quantity is not None:
            return self.price * self.quantity
        return 0 
    
    class Meta:
        verbose_name = "Элемент заказа"
        verbose_name_plural = "Элементы заказа"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    profile, created = UserProfile.objects.get_or_create(user=instance)
    if not created:
        profile.save()

class NotificationLog(models.Model):
    NOTIFICATION_TYPES = [
        ('order_created', 'Создан заказ'),
        ('payment_success', 'Успешная оплата'),
        ('order_cancelled', 'Заказ отменен'),
        ('telegram_sent', 'Отправлено в Telegram'),
        ('email_sent', 'Отправлено по email'),
        ('webhook_received', 'Получен webhook'),
        ('contact_form', 'Форма обратной связи'), 
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="Заказ", null=True, blank=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, verbose_name="Тип уведомления")
    message = models.TextField(verbose_name="Сообщение")
    sent_to = models.CharField(max_length=200, verbose_name="Получатель", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    success = models.BooleanField(default=True, verbose_name="Успешно")
    error_message = models.TextField(verbose_name="Ошибка", blank=True)
    
    def __str__(self):
        if self.order:
            return f"Уведомление #{self.id} для заказа #{self.order.id}"
        else:
            return f"Уведомление #{self.id} (без заказа)"
    
    class Meta:
        verbose_name = "Лог уведомлений"
        verbose_name_plural = "Логи уведомлений"
        ordering = ['-created_at']

class LoginAttempt(models.Model):
    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)
    
    @classmethod
    def is_ip_blocked(cls, ip_address):
        """Проверяет, заблокирован ли IP из-за множества неудачных попыток"""
        time_threshold = timezone.now() - timedelta(minutes=15)
        failed_attempts = cls.objects.filter(
            ip_address=ip_address,
            timestamp__gte=time_threshold,
            success=False
        ).count()
        return failed_attempts >= 5
    
class SecurityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField()

class Wishlist(models.Model):
    """Модель избранных товаров"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    def __str__(self):
        return f"Избранное {self.user.username}"
    
    def get_items_count(self):
        return self.wishlistitem_set.count()
    
    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранные товары"

class WishlistItem(models.Model):
    """Элемент избранного"""
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, verbose_name="Избранное")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")
    
    def __str__(self):
        return f"{self.product.name} в избранном {self.wishlist.user.username}"
    
    class Meta:
        verbose_name = "Элемент избранного"
        verbose_name_plural = "Элементы избранного"
        unique_together = ['wishlist', 'product']  # Один товар может быть только один раз

# Сигнал для создания избранного при создании пользователя
@receiver(post_save, sender=User)
def create_user_wishlist(sender, instance, created, **kwargs):
    if created:
        Wishlist.objects.get_or_create(user=instance)

class ProductReview(models.Model):
    RATING_CHOICES = [
        (1, '1 - Очень плохо'),
        (2, '2 - Плохо'),
        (3, '3 - Удовлетворительно'),
        (4, '4 - Хорошо'),
        (5, '5 - Отлично'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, verbose_name="Рейтинг")
    comment = models.TextField(verbose_name="Комментарий", max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    is_approved = models.BooleanField(default=False, verbose_name="Одобрен")
    is_moderated = models.BooleanField(default=False, verbose_name="Промодерирован")
    
    class Meta:
        verbose_name = "Отзыв о товаре"
        verbose_name_plural = "Отзывы о товарах"
        ordering = ['-created_at']
        unique_together = ['product', 'user']  # Один отзыв на товар от пользователя
    
    def __str__(self):
        return f"Отзыв {self.user.username} на {self.product.name} ({self.rating}/5)"
    
    def save(self, *args, **kwargs):
        if not self.is_moderated:
            self.is_approved = False
        super().save(*args, **kwargs)
    
    @classmethod
    def can_user_review(cls, user, product):
        """Проверяет, может ли пользователь оставить отзыв на товар"""
        # Пользователь должен быть авторизован
        if not user.is_authenticated:
            return False
        
        if settings.DEBUG:
            has_reviewed = cls.objects.filter(user=user, product=product).exists()
            return not has_reviewed
        
        # Проверяем, покупал ли пользователь этот товар
        has_purchased = OrderItem.objects.filter(
            order__user=user,
            order__status__in=['paid', 'processing', 'assembling', 'ready_for_shipping', 'shipped', 'delivered', 'completed'],
            product=product
        ).exists()
        
        # Проверяем, не оставлял ли уже отзыв
        has_reviewed = cls.objects.filter(user=user, product=product).exists()
        
        return has_purchased and not has_reviewed
    
    @classmethod
    def get_approved_reviews(cls, product):
        """Возвращает одобренные отзывы для товара"""
        return cls.objects.filter(product=product, is_approved=True)
    
    @classmethod
    def get_average_rating(cls, product):
        """Возвращает средний рейтинг товара"""
        from django.db.models import Avg
        result = cls.objects.filter(
            product=product, 
            is_approved=True
        ).aggregate(average=Avg('rating'))
        return result['average'] or 0