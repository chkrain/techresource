# main/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    phone = models.CharField(max_length=20, verbose_name="Телефон", blank=True)
    company = models.CharField(max_length=200, verbose_name="Компания", blank=True)
    position = models.CharField(max_length=100, verbose_name="Должность", blank=True)
    
    def __str__(self):
        return f"Профиль {self.user.username}"
    
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
            # Снимаем флаг default с других адресов этого пользователя
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Адрес"
        verbose_name_plural = "Адреса"

class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    description = models.TextField(verbose_name="Описание", blank=True)
    quantity = models.IntegerField(default=0, verbose_name="Остаток")
    category = models.CharField(max_length=100, verbose_name="Категория", blank=True)
    article = models.CharField(max_length=50, verbose_name="Артикул", blank=True)
    image = models.ImageField(upload_to='products/', verbose_name="Изображение", blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="Активный")
    
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
        ('shipped', 'Отправлен'),
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
    
    # Таймстампы
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата оплаты")
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата отмены")
    
    def __str__(self):
        return f"Заказ #{self.id} - {self.customer_name}"
    
    def can_be_cancelled(self):
        """Можно отменить заказ в течение 10 минут после оплаты"""
        from django.utils import timezone
        if self.status == 'paid' and self.paid_at:
            return (timezone.now() - self.paid_at).total_seconds() < 600  # 10 минут
        return False
    
    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="Заказ")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def get_total_price(self):
        return self.price * self.quantity
    
    class Meta:
        verbose_name = "Элемент заказа"
        verbose_name_plural = "Элементы заказа"

# Исправленные сигналы для создания профиля пользователя
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Используем get_or_create чтобы избежать ошибки если профиля нет
    UserProfile.objects.get_or_create(user=instance)
    instance.userprofile.save()