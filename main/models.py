# main/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date
from django.utils import timezone
import secrets
import hashlib
import time
from datetime import timedelta
from django.conf import settings
import json
import hmac
import base64
from decimal import Decimal
import struct

class UserProfile(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('individual', 'Физическое лицо'),
        ('legal', 'Юридическое лицо'),
    ]
    account_type = models.CharField(
        max_length=20, 
        choices=ACCOUNT_TYPE_CHOICES, 
        default='individual'
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE) 
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Телефон')
    company = models.CharField(max_length=100, blank=True, verbose_name='Компания')
    position = models.CharField(max_length=100, blank=True, verbose_name='Должность')
    date_of_birth = models.DateField(blank=True, null=True, verbose_name='Дата рождения')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Аватар')

    company_name = models.CharField(max_length=255, blank=True, null=True)
    inn = models.CharField(max_length=12, blank=True, null=True)
    kpp = models.CharField(max_length=9, blank=True, null=True)
    ogrn = models.CharField(max_length=13, blank=True, null=True)
    legal_address = models.TextField(blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    bik = models.CharField(max_length=9, blank=True, null=True)
    settlement_account = models.CharField(max_length=20, blank=True, null=True)
    correspondent_account = models.CharField(max_length=20, blank=True, null=True)
    
    # Поля для восстановления пароля
    phone_verified = models.BooleanField(default=False, verbose_name='Телефон подтвержден')
    sms_code = models.CharField(max_length=6, blank=True, null=True, verbose_name='Код из SMS')
    sms_code_expires = models.DateTimeField(blank=True, null=True, verbose_name='Код действует до')
    reset_token = models.CharField(max_length=100, blank=True, null=True, verbose_name='Токен сброса')
    reset_token_expires = models.DateTimeField(blank=True, null=True, verbose_name='Токен действует до')
    
    # Новые поля для безопасности
    password_changed_at = models.DateTimeField(default=timezone.now, verbose_name='Дата смены пароля')
    email_verified = models.BooleanField(default=False, verbose_name='Email подтвержден')
    verification_token = models.CharField(max_length=100, blank=True, null=True)
    verification_token_created = models.DateTimeField(blank=True, null=True)
    last_security_notification = models.DateTimeField(blank=True, null=True)
    
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

class Admin2FA(models.Model):
    """2FA для администраторов (упрощенная версия без pyotp)"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_enabled = models.BooleanField(default=False, verbose_name='2FA включена')
    secret_key = models.CharField(max_length=32, blank=True, verbose_name='Секретный ключ')
    backup_codes = models.JSONField(default=list, verbose_name='Резервные коды')
    last_used = models.DateTimeField(null=True, blank=True, verbose_name='Последнее использование')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    def __str__(self):
        return f"2FA для {self.user.username}"
    
    def generate_secret_key(self):
        """Генерация секретного ключа"""
        self.secret_key = base64.b32encode(secrets.token_bytes(20)).decode('utf-8').rstrip('=')
        self.is_enabled = False
        self.save()
        return self.secret_key
    
    def generate_backup_codes(self):
        """Генерация резервных кодов"""
        # Генерируем 8-символьные коды для удобства
        self.backup_codes = [secrets.token_hex(4).upper() for _ in range(8)]  # 8-символьные коды
        self.save()
        return self.backup_codes
    
    def verify_backup_code(self, code):
        """Проверка резервного кода"""
        if not self.backup_codes:
            return False
        
        code = code.strip().upper()
        if code in self.backup_codes:
            # Удаляем использованный код
            self.backup_codes.remove(code)
            self.save()
            return True
        return False
    
    def generate_totp(self, timestamp=None):
        """Генерация TOTP кода"""
        if not self.secret_key:
            return None
        
        if timestamp is None:
            timestamp = int(time.time())
        
        time_step = 30
        T = timestamp // time_step
        
        try:
            secret_key = self.secret_key
            padding = 8 - (len(secret_key) % 8)
            if padding != 8:
                secret_key += '=' * padding
            
            key = base64.b32decode(secret_key)
            
            msg = struct.pack('>Q', T)
            hmac_result = hmac.new(key, msg, hashlib.sha1).digest()
            
            offset = hmac_result[-1] & 0xf
            binary = struct.unpack('>I', hmac_result[offset:offset+4])[0] & 0x7fffffff
            
            otp = binary % 1000000
            return str(otp).zfill(6)
            
        except Exception as e:
            print(f"❌ Ошибка генерации TOTP: {e}")
            return None
    
    def verify_totp(self, code, valid_window=1):
        """Проверка TOTP кода"""
        if not self.secret_key:
            return False
        
        code = code.strip()
        timestamp = int(time.time())
        for i in range(-valid_window, valid_window + 1):
            expected_code = self.generate_totp(timestamp + i * 30)
            print(f"🔍 Проверка кода: введен '{code}', ожидается '{expected_code}' (сдвиг {i})")
            if code == expected_code:
                print("✅ Код верный!")
                return True
        
        print("❌ Код неверный!")
        return False
    
    def get_provisioning_uri(self, username, issuer_name):
        """Генерация URI для QR-кода"""
        return f"otpauth://totp/{issuer_name}:{username}?secret={self.secret_key}&issuer={issuer_name}"
    
    class Meta:
        verbose_name = "2FA администратора"
        verbose_name_plural = "2FA администраторов"

class SecurityLog(models.Model):
    """Расширенный лог безопасности"""
    ACTION_CHOICES = [
        ('login', 'Вход в систему'),
        ('login_failed', 'Неудачная попытка входа'),
        ('logout', 'Выход из системы'),
        ('password_change', 'Смена пароля'),
        ('password_reset_request', 'Запрос сброса пароля'),
        ('password_reset_success', 'Успешный сброс пароля'),
        ('profile_update', 'Обновление профиля'),
        ('register', 'Регистрация'),
        ('register_failed', 'Неудачная регистрация'),
        ('email_verification', 'Подтверждение email'),
        ('payment_attempt', 'Попытка оплаты'),
        ('payment_success', 'Успешная оплата'),
        ('payment_failed', 'Неудачная оплата'),
        ('admin_access', 'Доступ к админке'),
        ('suspicious_activity', 'Подозрительная активность'),
        ('fraud_attempt', 'Попытка мошенничества'),
        ('webhook_received', 'Получен webhook'),
        ('api_access', 'Доступ к API'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Пользователь")
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, verbose_name="Действие")
    ip_address = models.GenericIPAddressField(verbose_name="IP-адрес")
    user_agent = models.TextField(verbose_name="User Agent", blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время")
    success = models.BooleanField(default=True, verbose_name="Успешно")
    details = models.JSONField(default=dict, verbose_name="Детали")
    risk_level = models.CharField(
        max_length=10, 
        choices=[('low', 'Низкий'), ('medium', 'Средний'), ('high', 'Высокий')],
        default='low',
        verbose_name="Уровень риска"
    )
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.user.username if self.user else 'Аноним'} - {self.timestamp}"
    
    class Meta:
        verbose_name = "Лог безопасности"
        verbose_name_plural = "Логи безопасности"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]

class PaymentAuditLog(models.Model):
    """Аудит платежных операций"""
    ACTION_CHOICES = [
        ('payment_created', 'Платеж создан'),
        ('payment_succeeded', 'Платеж успешен'),
        ('payment_failed', 'Платеж не удался'),
        ('refund_created', 'Возврат создан'),
        ('refund_succeeded', 'Возврат успешен'),
        ('webhook_received', 'Webhook получен'),
        ('webhook_processed', 'Webhook обработан'),
        ('amount_mismatch', 'Несоответствие суммы'),
        ('duplicate_payment', 'Дублирующий платеж'),
    ]
    
    order = models.ForeignKey('Order', on_delete=models.CASCADE, verbose_name="Заказ")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Действие")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Пользователь")
    ip_address = models.GenericIPAddressField(verbose_name="IP-адрес")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    details = models.JSONField(default=dict, verbose_name="Детали")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    def __str__(self):
        return f"Аудит платежа #{self.order.id} - {self.get_action_display()}"
    
    class Meta:
        verbose_name = "Аудит платежа"
        verbose_name_plural = "Аудит платежей"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

class RateLimitLog(models.Model):
    """Лог ограничения частоты запросов"""
    key = models.CharField(max_length=255, verbose_name="Ключ ограничения")
    ip_address = models.GenericIPAddressField(verbose_name="IP-адрес")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Пользователь")
    action = models.CharField(max_length=100, verbose_name="Действие")
    attempts = models.IntegerField(default=1, verbose_name="Попытки")
    window_start = models.DateTimeField(verbose_name="Начало окна")
    window_end = models.DateTimeField(verbose_name="Конец окна")
    blocked_until = models.DateTimeField(null=True, blank=True, verbose_name="Заблокировано до")
    
    def __str__(self):
        return f"RateLimit: {self.key} - {self.ip_address}"
    
    class Meta:
        verbose_name = "Лог ограничения запросов"
        verbose_name_plural = "Логи ограничения запросов"
        indexes = [
            models.Index(fields=['key', 'window_start']),
            models.Index(fields=['ip_address', 'window_start']),
        ]

class FraudDetectionLog(models.Model):
    """Лог обнаружения мошенничества"""
    SEVERITY_CHOICES = [
        ('low', 'Низкая'),
        ('medium', 'Средняя'),
        ('high', 'Высокая'),
        ('critical', 'Критическая'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Пользователь")
    order = models.ForeignKey('Order', on_delete=models.CASCADE, null=True, blank=True, verbose_name="Заказ")
    ip_address = models.GenericIPAddressField(verbose_name="IP-адрес")
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, verbose_name="Серьезность")
    description = models.TextField(verbose_name="Описание")
    reasons = models.JSONField(default=list, verbose_name="Причины")
    detected_at = models.DateTimeField(auto_now_add=True, verbose_name="Обнаружено")
    resolved = models.BooleanField(default=False, verbose_name="Решено")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Решено в")
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='resolved_fraud_cases', verbose_name="Решено кем")
    
    def __str__(self):
        return f"Мошенничество: {self.get_severity_display()} - {self.ip_address}"
    
    class Meta:
        verbose_name = "Лог мошенничества"
        verbose_name_plural = "Логи мошенничества"
        ordering = ['-detected_at']

class CSPViolationReport(models.Model):
    """Отчет о нарушениях Content Security Policy"""
    document_uri = models.URLField(verbose_name="URI документа")
    violated_directive = models.CharField(max_length=100, verbose_name="Нарушенная директива")
    effective_directive = models.CharField(max_length=100, verbose_name="Эффективная директива")
    original_policy = models.TextField(verbose_name="Оригинальная политика")
    blocked_uri = models.URLField(blank=True, null=True, verbose_name="Заблокированный URI")
    source_file = models.CharField(max_length=255, blank=True, verbose_name="Исходный файл")
    line_number = models.IntegerField(null=True, blank=True, verbose_name="Номер строки")
    column_number = models.IntegerField(null=True, blank=True, verbose_name="Номер колонки")
    user_agent = models.TextField(verbose_name="User Agent")
    ip_address = models.GenericIPAddressField(verbose_name="IP-адрес")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    def __str__(self):
        return f"CSP Violation: {self.violated_directive} - {self.document_uri}"
    
    class Meta:
        verbose_name = "Отчет CSP"
        verbose_name_plural = "Отчеты CSP"
        ordering = ['-created_at']

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    title = models.CharField(max_length=100, verbose_name="Название адреса", default="Основной")
    full_name = models.CharField(max_length=200, verbose_name="ФИО")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    address = models.TextField(verbose_name="Адрес")
    city = models.CharField(max_length=100, verbose_name="Город")
    postal_code = models.CharField(max_length=20, verbose_name="Почтовый индекс")
    is_default = models.BooleanField(default=False, verbose_name="Адрес по умолчанию")

    region = models.CharField(max_length=100, verbose_name="Регион", blank=True)
    country = models.CharField(max_length=100, verbose_name="Страна", default="Россия")
    delivery_zone = models.CharField(
        max_length=20, 
        choices=[
            ('central', 'Центральный'),
            ('far_east', 'Дальний восток'), 
            ('siberia', 'Сибирь'),
            ('ural', 'Урал'),
            ('south', 'Юг'),
            ('north_west', 'Северо-Запад'),
        ],
        blank=True,
        verbose_name="Зона доставки"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    def __str__(self):
        return f"{self.title} - {self.city}"
    
    def save(self, *args, **kwargs):
        if self.city and not self.delivery_zone:
            self.delivery_zone = self.detect_delivery_zone()
        
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

    def detect_delivery_zone(self):
        city_zones = {
            'central': ['москва', 'санкт-петербург', 'тверь', 'ярославль', 'кострома', 'иваново', 'владимир'],
            'south': ['ростов', 'краснодар', 'сочи', 'волгоград', 'астрахань'],
            'north_west': ['псков', 'новгород', 'калининград', 'мурманск'],
            'ural': ['екатеринбург', 'челябинск', 'пермь', 'тюмень'],
            'siberia': ['новосибирск', 'омск', 'красноярск', 'иркутск'],
            'far_east': ['владивосток', 'хабаровск', 'якутск']
        }
        
        city_lower = self.city.lower()
        for zone, cities in city_zones.items():
            if any(city in city_lower for city in cities):
                return zone
        
        return 'central' 
    
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
    
    brand = models.CharField(max_length=100, verbose_name="Бренд", blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name="Рейтинг")
    popularity = models.IntegerField(default=0, verbose_name="Популярность")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="Вес")
    dimensions = models.CharField(max_length=50, blank=True, verbose_name="Габариты")
    material = models.CharField(max_length=100, blank=True, verbose_name="Материал")
    warranty = models.IntegerField(default=12, verbose_name="Гарантия (мес)")

    weight = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0.1,
        verbose_name="Вес (кг)"
    )
    dimensions = models.CharField(
        max_length=50, 
        blank=True, 
        verbose_name="Габариты (Д×Ш×В см)"
    )
    vat_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=20.00,
        verbose_name="Ставка НДС (%)"
    )
    is_fragile = models.BooleanField(default=False, verbose_name="Хрупкий товар")
    requires_special_delivery = models.BooleanField(default=False, verbose_name="Требует спецдоставки")

    
    # Новые поля для безопасности
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    last_restock = models.DateTimeField(null=True, blank=True, verbose_name="Последнее пополнение")

    specifications = models.JSONField(default=dict, blank=True, verbose_name="Характеристики")
    
    def save(self, *args, **kwargs):
        # Автоматически рассчитываем цену без НДС
        if self.price and self.vat_rate:
            self.price_without_vat = self.price / (1 + self.vat_rate / 100)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    def get_main_image(self):
        """Возвращает основное изображение товара"""
        main_image = self.images.filter(is_main=True).first()
        if main_image:
            return main_image
        first_image = self.images.first()
        if first_image:
            return first_image
        return None
    
    def get_images_count(self):
        """Возвращает количество изображений товара"""
        return self.images.count()
    
    def get_images(self):
        """Возвращает все изображения товара в правильном порядке"""
        return self.images.all().order_by('order', 'created_at')
    
    def get_display_image(self):
        """Возвращает изображение для отображения в каталоге и корзине"""
        main_image = self.images.filter(is_main=True).first()
        if main_image:
            return main_image.image
        
        first_image = self.images.first()
        if first_image:
            return first_image.image
        
        return None
    
    def get_display_image_url(self):
        """Возвращает URL изображения или None"""
        display_image = self.get_display_image()
        if display_image:
            return display_image.url
        return None
    
    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'category']),
            models.Index(fields=['price', 'is_active']),
        ]

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/', verbose_name="Изображение")
    order = models.IntegerField(default=0, verbose_name="Порядок")
    is_main = models.BooleanField(default=False, verbose_name="Основное изображение")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товаров"
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"Изображение {self.id} для {self.product.name}"

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
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
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def get_total_price(self):
        return self.product.price * self.quantity
    
    class Meta:
        verbose_name = "Элемент корзины"
        verbose_name_plural = "Элементы корзины"
        unique_together = ['cart', 'product']

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
        ('disputed', 'Оспаривается'),
    ]
    
    PAYMENT_METHODS = [
        ('invoice', 'По счету'),  
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Общая сумма")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='card', verbose_name="Способ оплаты")

    # Данные доставки
    customer_name = models.CharField(max_length=100, verbose_name="Имя клиента")
    customer_phone = models.CharField(max_length=20, verbose_name="Телефон")
    customer_email = models.EmailField(verbose_name="Email")
    delivery_address = models.TextField(verbose_name="Адрес доставки")

    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=20.00,  verbose_name="Ставка НДС (%)")
    price_without_vat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена без НДС", help_text="Рассчитывается автоматически")
    
    # Новые поля для отслеживания
    status_changed_at = models.DateTimeField(auto_now=True, verbose_name="Время изменения статуса")
    tracking_number = models.CharField(max_length=100, blank=True, verbose_name="Трек-номер")
    shipping_company = models.CharField(max_length=100, blank=True, verbose_name="Служба доставки")
    estimated_delivery = models.DateField(null=True, blank=True, verbose_name="Примерная дата доставки")

    payment_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Комиссия платежной системы")
    delivery_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Стоимость доставки")
    final_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Итоговая сумма с учетом доставки и комиссий")
    
    # Таймстампы
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата оплаты")
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата отмены")
    
    # Новые поля для безопасности
    fraud_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Оценка мошенничества")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP-адрес создания")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")

    vat_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="Сумма НДС"
    )
    total_without_vat = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="Сумма без НДС"
    )

    paid_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, 
        verbose_name="Оплаченная сумма"
    )
    is_payment_finalized = models.BooleanField(
        default=False, verbose_name="Оплата завершена"
    )
    net_revenue = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name="Чистая выручка (без доставки и комиссий)"
    )

    def calculate_vat(self):
        """Рассчитывает НДС для заказа"""
        vat_total = Decimal('0')
        total_without_vat = Decimal('0')
        
        for item in self.orderitem_set.all():
            if hasattr(item, 'vat_amount'):
                vat_total += item.vat_amount
                total_without_vat += item.price_without_vat * item.quantity
        
        self.vat_amount = vat_total
        self.total_without_vat = total_without_vat
        self.save()
    
    def finalize_payment(self): 
        """Фиксирует оплату при смене статуса на 'paid'"""
        if self.status == 'paid' and not self.is_payment_finalized:
            self.paid_amount = self.final_price
            self.net_revenue = self.total_price  # Только стоимость товаров
            self.is_payment_finalized = True
            self.paid_at = timezone.now()
            self.save()
    
    def get_clean_revenue(self):
        """Возвращает чистую выручку"""
        return self.net_revenue if self.is_payment_finalized else 0

    def __str__(self):
        return f"Заказ #{self.id} - {self.customer_name}"
    
    def get_final_price_with_fees(self):
        """Возвращает итоговую сумму с учетом доставки и комиссий"""
        return self.total_price + self.delivery_cost + self.payment_fee
    
    def get_fee_breakdown(self):
        """Возвращает детализацию стоимости"""
        return {
            'subtotal': self.total_price,
            'delivery': self.delivery_cost,
            'payment_fee': self.payment_fee,
            'total': self.get_final_price_with_fees()
        }
    
    def can_be_cancelled(self):
        """Можно отменить заказ в течение 10 минут после оплаты"""
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
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['payment_method', 'created_at']),
        ]

class OrderStatusLog(models.Model):
    """Лог изменений статуса заказа"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="Заказ")
    old_status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES, verbose_name="Предыдущий статус")
    new_status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES, verbose_name="Новый статус")
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Изменил")
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="Время изменения")
    notes = models.TextField(blank=True, verbose_name="Примечания")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP-адрес")
    
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

    vat_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=20.00,
        verbose_name="Ставка НДС (%)"
    )
    vat_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="Сумма НДС"
    )
    price_without_vat = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,  
        verbose_name="Цена без НДС",
        help_text="Рассчитывается автоматически"
    )
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def get_total_price(self):
        if self.price is not None and self.quantity is not None:
            return self.price * self.quantity
        return 0 
    
    def save(self, *args, **kwargs):
        # Рассчитываем НДС и цену без НДС
        if self.price and self.quantity and self.vat_rate:
            total = self.price * self.quantity
            self.vat_amount = total * (self.vat_rate / 100) / (1 + self.vat_rate / 100)
            self.price_without_vat = self.price / (1 + self.vat_rate / 100)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Элемент заказа"
        verbose_name_plural = "Элементы заказа"

class NotificationLog(models.Model):
    NOTIFICATION_TYPES = [
        ('order_created', 'Создан заказ'),
        ('payment_success', 'Успешная оплата'),
        ('order_cancelled', 'Заказ отменен'),
        ('telegram_sent', 'Отправлено в Telegram'),
        ('email_sent', 'Отправлено по email'),
        ('webhook_received', 'Получен webhook'),
        ('contact_form', 'Форма обратной связи'),
        ('security_alert', 'Предупреждение безопасности'),
        ('fraud_alert', 'Предупреждение мошенничества'),
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
    
    class Meta:
        indexes = [
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['username', 'timestamp']),
        ]

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField()
    
    class Meta:
        indexes = [
            models.Index(fields=['token', 'expires_at']),
        ]

class Wishlist(models.Model):
    """Модель избранных товаров"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
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
        unique_together = ['wishlist', 'product']

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
    
    # Новые поля для безопасности
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP-адрес")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    
    class Meta:
        verbose_name = "Отзыв о товаре"
        verbose_name_plural = "Отзывы о товарах"
        ordering = ['-created_at']
        unique_together = ['product', 'user']
    
    def __str__(self):
        return f"Отзыв {self.user.username} на {self.product.name} ({self.rating}/5)"
    
    def save(self, *args, **kwargs):
        if not self.is_moderated:
            self.is_approved = False
        super().save(*args, **kwargs)
    
    @classmethod
    def can_user_review(cls, user, product):
        """Проверяет, может ли пользователь оставить отзыв на товар"""
        if not user.is_authenticated:
            return False
        
        if settings.DEBUG:
            has_reviewed = cls.objects.filter(user=user, product=product).exists()
            return not has_reviewed
        
        has_purchased = OrderItem.objects.filter(
            order__user=user,
            order__status__in=['paid', 'processing', 'assembling', 'ready_for_shipping', 'shipped', 'delivered', 'completed'],
            product=product
        ).exists()
        
        has_reviewed = cls.objects.filter(user=user, product=product).exists()
        
        return has_purchased and not has_reviewed
    
    @classmethod
    def get_approved_reviews(cls, product):
        return cls.objects.filter(product=product, is_approved=True)
    
    @classmethod
    def get_average_rating(cls, product):
        from django.db.models import Avg
        result = cls.objects.filter(
            product=product, 
            is_approved=True
        ).aggregate(average=Avg('rating'))
        return result['average'] or 0

class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('in_progress', 'В обработке'),
        ('resolved', 'Решена'),
        ('closed', 'Закрыта'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('medium', 'Средний'),
        ('high', 'Высокий'),
        ('critical', 'Критический'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    subject = models.CharField(max_length=200, verbose_name='Тема')
    description = models.TextField(verbose_name='Описание проблемы')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name='Приоритет')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP-адрес')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    screen_resolution = models.CharField(max_length=20, blank=True, null=True)
    timezone = models.CharField(max_length=50, blank=True, null=True)
    cookies_enabled = models.BooleanField(default=False)
    javascript_enabled = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Заявка в поддержку'
        verbose_name_plural = 'Заявки в поддержку'
        ordering = ['-created_at']

    def __str__(self):
        return f"Заявка #{self.id} - {self.subject}"

class SupportAttachment(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='support_attachments/%Y/%m/%d/', verbose_name='Файл')
    file_name = models.CharField(max_length=255, verbose_name='Имя файла')
    file_size = models.IntegerField(verbose_name='Размер файла')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата загрузки')
    
    class Meta:
        verbose_name = 'Вложение заявки'
        verbose_name_plural = 'Вложения заявок'

    def __str__(self):
        return self.file_name

    def save(self, *args, **kwargs):
        if not self.file_name and self.file:
            self.file_name = self.file.name
        super().save(*args, **kwargs)

# Сигналы
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    profile, created = UserProfile.objects.get_or_create(user=instance)
    if not created:
        profile.save()

@receiver(post_save, sender=User)
def create_user_wishlist(sender, instance, created, **kwargs):
    if created:
        Wishlist.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def create_admin_2fa(sender, instance, created, **kwargs):
    """Создание записи 2FA для администраторов"""
    if created and instance.is_staff:
        Admin2FA.objects.get_or_create(user=instance)


class ServicePage(models.Model):
    """Модель для дополнительных динамических страниц услуг"""
    PAGE_TYPES = [
        ('main_service', 'Основная услуга'),
        ('sub_service', 'Подуслуга'), 
        ('instruction', 'Инструкция'),
    ]
    
    # Связь со статической страницей (если есть)
    STATIC_SERVICES = [
        ('', '--- Не привязано ---'),
        ('design', 'Проектирование систем'),
        ('electrical', 'Электромонтажные работы'),
        ('software', 'Разработка ПО и SCADA'),
        ('equipment', 'Поставка оборудования'), 
        ('support', 'Техническая поддержка'),
        ('maintenance', 'Сервисное обслуживание'),
    ]
    
    static_service = models.CharField(
        max_length=20, 
        choices=STATIC_SERVICES, 
        blank=True, 
        default='',
        verbose_name="Привязать к статической странице"
    )
    
    title = models.CharField(max_length=200, verbose_name="Заголовок страницы")
    slug = models.SlugField(unique=True, verbose_name="URL-адрес")
    page_type = models.CharField(max_length=20, choices=PAGE_TYPES, default='main_service', verbose_name="Тип страницы")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                             verbose_name="Родительская страница", related_name='children')
    
    # Контент
    hero_title = models.CharField(max_length=200, blank=True, verbose_name="Заголовок героя")
    hero_subtitle = models.TextField(blank=True, verbose_name="Подзаголовок героя")
    hero_image = models.ImageField(upload_to='service_heroes/', blank=True, null=True, verbose_name="Изображение героя")
    content = models.TextField(blank=True, verbose_name="Основной контент")
    
    # Исправляем features - используем TextField для простоты
    features_text = models.TextField(
        blank=True, 
        verbose_name="Особенности",
        help_text="Каждая особенность с новой строки. Формат: Заголовок|Описание (разделитель - вертикальная черта)"
    )
    
    # SEO и настройки
    meta_description = models.TextField(blank=True, verbose_name="Мета-описание")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    show_in_navigation = models.BooleanField(default=True, verbose_name="Показывать в навигации")
    order = models.IntegerField(default=0, verbose_name="Порядок сортировки")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Дополнительная страница услуги"
        verbose_name_plural = "Дополнительные страницы услуг"
        ordering = ['order', 'title']
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        """Генерируем URL в зависимости от типа и привязки"""
        if self.static_service:
            # Если привязано к статической странице
            base_url = f"/services/{self.static_service}/"
            if self.page_type == 'instruction' and self.parent:
                return f"{base_url}instructions/{self.slug}/"
            elif self.parent:
                return f"{base_url}{self.slug}/"
            else:
                return base_url
        else:
            # Динамические страницы
            if self.page_type == 'instruction' and self.parent:
                return f"/services/dynamic/{self.parent.slug}/instructions/{self.slug}/"
            elif self.parent:
                return f"/services/dynamic/{self.parent.slug}/{self.slug}/"
            else:
                return f"/services/dynamic/{self.slug}/"
    
    def get_static_url(self):
        """Получить URL статической страницы"""
        if self.static_service:
            return f"/services/{self.static_service}/"
        return None
    
    def get_breadcrumbs(self):
        breadcrumbs = []
        if self.parent:
            breadcrumbs.extend(self.parent.get_breadcrumbs())
        
        breadcrumbs.append({
            'title': self.title, 
            'url': self.get_absolute_url()
        })
        return breadcrumbs
    
    def get_features_list(self):
        """Получить особенности из текстового поля"""
        if not self.features_text:
            return []
        
        features = []
        for line in self.features_text.strip().split('\n'):
            line = line.strip()
            if line:
                # Разделяем по вертикальной черте
                if '|' in line:
                    title, description = line.split('|', 1)
                    features.append({
                        'title': title.strip(),
                        'description': description.strip()
                    })
                else:
                    features.append({
                        'title': line,
                        'description': ''
                    })
        return features
    
    @classmethod
    def get_navigation_tree(cls):
        """Получить дерево навигации включая статические страницы"""
        navigation = []
        
        # Статические страницы (основные услуги)
        static_services = [
            {
                'title': 'Проектирование систем',
                'url': '/services/design/',
                'slug': 'design',
                'static': True,
                'children': cls.objects.filter(
                    static_service='design',
                    page_type='sub_service',
                    is_active=True,
                    show_in_navigation=True
                ).order_by('order')
            },
            {
                'title': 'Электромонтажные работы', 
                'url': '/services/electrical/',
                'slug': 'electrical',
                'static': True,
                'children': cls.objects.filter(
                    static_service='electrical', 
                    page_type='sub_service',
                    is_active=True,
                    show_in_navigation=True
                ).order_by('order')
            },
            {
                'title': 'Разработка ПО и SCADA',
                'url': '/services/software/',
                'slug': 'software', 
                'static': True,
                'children': cls.objects.filter(
                    static_service='software',
                    page_type='sub_service', 
                    is_active=True,
                    show_in_navigation=True
                ).order_by('order')
            },
            {
                'title': 'Поставка оборудования',
                'url': '/services/equipment/',
                'slug': 'equipment',
                'static': True,
                'children': cls.objects.filter(
                    static_service='equipment',
                    page_type='sub_service',
                    is_active=True,
                    show_in_navigation=True
                ).order_by('order')
            },
            {
                'title': 'Техническая поддержка',
                'url': '/services/support/',
                'slug': 'support',
                'static': True,
                'children': cls.objects.filter(
                    static_service='support',
                    page_type='sub_service',
                    is_active=True, 
                    show_in_navigation=True
                ).order_by('order')
            },
            {
                'title': 'Сервисное обслуживание',
                'url': '/services/maintenance/',
                'slug': 'maintenance',
                'static': True,
                'children': cls.objects.filter(
                    static_service='maintenance',
                    page_type='sub_service',
                    is_active=True,
                    show_in_navigation=True
                ).order_by('order')
            }
        ]
        
        # Динамические основные услуги (без привязки к статическим)
        dynamic_services = cls.objects.filter(
            page_type='main_service',
            static_service='',  # Не привязаны к статическим
            is_active=True,
            show_in_navigation=True
        ).order_by('order')
        
        # Объединяем статические и динамические
        for static in static_services:
            nav_item = {
                'title': static['title'],
                'url': static['url'],
                'slug': static['slug'],
                'static': True,
                'children': []
            }
            
            for child in static['children']:
                child_data = {
                    'title': child.title,
                    'url': child.get_absolute_url(),
                    'slug': child.slug,
                    'children': child.children.filter(
                        is_active=True,
                        show_in_navigation=True
                    ).order_by('order')
                }
                nav_item['children'].append(child_data)
            
            navigation.append(nav_item)
        
        # Добавляем динамические услуги
        for service in dynamic_services:
            nav_item = {
                'title': service.title,
                'url': service.get_absolute_url(),
                'slug': service.slug,
                'static': False,
                'children': service.children.filter(
                    page_type='sub_service',
                    is_active=True,
                    show_in_navigation=True
                ).order_by('order')
            }
            navigation.append(nav_item)
        
        return navigation