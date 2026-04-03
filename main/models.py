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
from datetime import timedelta, datetime
from django.conf import settings
import hmac
import base64
from decimal import Decimal
import struct
from django.db.models.signals import pre_save
from django.utils.text import slugify
import re
from PIL import Image
from django.core.cache import cache
import requests
import uuid
from django.contrib.auth import get_user_model
import os
from django.core.exceptions import ValidationError
from django.utils.html import escape
from .validators import validate_avatar, validate_profile_background
from django.urls import reverse

User = get_user_model()

class CurrencyRate(models.Model):
    """Модель для хранения курсов валют"""
    CURRENCY_CHOICES = [
        ('RUB', 'Российский рубль'),
        ('USD', 'Доллар США'),
        ('EUR', 'Евро'),
    ]
    
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, unique=True, verbose_name="Валюта")
    rate_to_rub = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Курс к рублю")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")
    is_active = models.BooleanField(default=True, verbose_name="Активный курс")
    
    class Meta:
        verbose_name = "Курс валюты"
        verbose_name_plural = "Курсы валют"
        ordering = ['currency']
    
    def __str__(self):
        return f"{self.get_currency_display()} = {self.rate_to_rub} RUB"
    
    @classmethod
    def update_rates_from_cbr(cls):
        """Обновление курсов валют с сайта ЦБ РФ"""
        try:
            url = 'https://www.cbr-xml-daily.ru/daily_json.js'
            response = requests.get(url, timeout=10)
            data = response.json()
            
            usd_rate = Decimal(str(data['Valute']['USD']['Value'])) / Decimal(str(data['Valute']['USD']['Nominal']))
            cls.objects.update_or_create(
                currency='USD',
                defaults={'rate_to_rub': usd_rate}
            )
            
            eur_rate = Decimal(str(data['Valute']['EUR']['Value'])) / Decimal(str(data['Valute']['EUR']['Nominal']))
            cls.objects.update_or_create(
                currency='EUR',
                defaults={'rate_to_rub': eur_rate}
            )
            
            cls.objects.update_or_create(
                currency='RUB',
                defaults={'rate_to_rub': Decimal('1.0000')}
            )
            
            return True
        except Exception as e:
            return False
    
    @classmethod
    def get_rate(cls, currency_code):
        """Получение курса валюты с кэшированием"""
        cache_key = f"currency_rate_{currency_code}"
        rate = cache.get(cache_key)
        
        if rate is None:
            try:
                currency = cls.objects.get(currency=currency_code, is_active=True)
                rate = currency.rate_to_rub
                cache.set(cache_key, rate, 3600)  # Кэшируем на 1 час
            except cls.DoesNotExist:
                rate = Decimal('1.0000')
        
        return rate
    
    @classmethod
    def convert_to_rub(cls, amount, from_currency):
        """Конвертация в рубли"""
        if from_currency == 'RUB':
            return amount
        
        rate = cls.get_rate(from_currency)
        return amount * rate
    
    @classmethod
    def convert_from_rub(cls, amount, to_currency):
        """Конвертация из рублей"""
        if to_currency == 'RUB':
            return amount
        
        rate = cls.get_rate(to_currency)
        if rate == 0:
            return amount
        
        return amount / rate

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
    company = models.CharField(max_length=100, blank=True, verbose_name='Компания', null=True)
    position = models.CharField(max_length=100, blank=True, verbose_name='Должность', null=True)
    date_of_birth = models.DateField(blank=True, null=True, verbose_name='Дата рождения')

    company_name = models.CharField(max_length=255, blank=True, null=True)
    inn = models.CharField(max_length=12, blank=True, null=True)
    kpp = models.CharField(max_length=9, blank=True, null=True)
    ogrn = models.CharField(max_length=13, blank=True, null=True)
    legal_address = models.TextField(blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    bik = models.CharField(max_length=9, blank=True, null=True)
    settlement_account = models.CharField(max_length=20, blank=True, null=True)
    correspondent_account = models.CharField(max_length=20, blank=True, null=True)
    
    phone_verified = models.BooleanField(default=False, verbose_name='Телефон подтвержден')
    sms_code = models.CharField(max_length=6, blank=True, null=True, verbose_name='Код из SMS')
    sms_code_expires = models.DateTimeField(blank=True, null=True, verbose_name='Код действует до')
    reset_token = models.CharField(max_length=100, blank=True, null=True, verbose_name='Токен сброса')
    reset_token_expires = models.DateTimeField(blank=True, null=True, verbose_name='Токен действует до')
    
    password_changed_at = models.DateTimeField(default=timezone.now, verbose_name='Дата смены пароля')
    email_verified = models.BooleanField(default=False, verbose_name='Email подтвержден')
    verification_token = models.CharField(max_length=100, blank=True, null=True)
    verification_token_created = models.DateTimeField(blank=True, null=True)
    last_security_notification = models.DateTimeField(blank=True, null=True)

    has_detailed_consent = models.BooleanField(
        default=False,
        verbose_name="Имеет подробное согласие"
    )
    
    detailed_consent_date = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Дата подписания подробного согласия"
    )
    
    last_privacy_update = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Последнее обновление настроек приватности"
    )
    
    PRIVACY_CHOICES = [
        ('public', 'Публично'),
        ('private', 'Только мне'),
        ('friends', 'Друзьям'),
        ('registered', 'Зарегистрированным'),
    ]
    
    privacy_mode = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='public',
        verbose_name='Режим приватности'
    )
    
    public_bio = models.TextField(
        blank=True,
        verbose_name='Публичная биография',
        max_length=1000,
        help_text='Будет видна другим пользователям'
    )
    
    public_skills = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Публичные навыки',
        help_text='Навыки через запятую'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен',
        help_text='Активен ли профиль'
    )
    
    public_links = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Публичные ссылки',
        help_text='Список ссылок в формате [{"name": "GitHub", "url": "https://..."}]'
    )
    
    private_notes = models.TextField(
        blank=True,
        verbose_name='Личные заметки',
        help_text='Только для вашего просмотра'
    )

    email_visibility = models.CharField(
        max_length=20,
        choices=PRIVACY_CHOICES,
        default='private',
        verbose_name='Видимость email'
    )
    
    phone_visibility = models.CharField(
        max_length=20,
        choices=PRIVACY_CHOICES,
        default='private',
        verbose_name='Видимость телефона'
    )
    
    company_visibility = models.CharField(
        max_length=20,
        choices=PRIVACY_CHOICES,
        default='public',
        verbose_name='Видимость компании'
    )
    
    position_visibility = models.CharField(
        max_length=20,
        choices=PRIVACY_CHOICES,
        default='public',
        verbose_name='Видимость должности'
    )
    
    skills_visibility = models.CharField(
        max_length=20,
        choices=PRIVACY_CHOICES,
        default='public',
        verbose_name='Видимость навыков'
    )
    
    activity_visibility = models.CharField(
        max_length=20,
        choices=PRIVACY_CHOICES,
        default='public',
        verbose_name='Видимость активности'
    )
    
    PROFILE_TAGS = [
        ('customer', 'Клиент'),
        ('partner', 'Партнер'),
        ('developer', 'Разработчик'),
        ('supplier', 'Поставщик'),
        ('carrier', 'Перевозчик'),
        ('contractor', 'Подрядчик'),
        ('investor', 'Инвестор'),
        ('employee', 'Сотрудник'),
        ('vip', 'VIP клиент'),
    ]
    
    profile_tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Теги профиля',
        help_text='Теги назначаются администратором'
    )
    
    profile_theme = models.CharField(
        max_length=50,
        default='default',
        verbose_name='Тема профиля',
        help_text='Цветовая тема профиля'
    )
    
    profile_background = models.ImageField(
        upload_to='profile_backgrounds/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Фон профиля',
        validators=[validate_profile_background]
    )
    
    show_statistics = models.BooleanField(
        default=True,
        verbose_name='Показывать статистику'
    )
    
    show_recent_activity = models.BooleanField(
        default=True,
        verbose_name='Показывать активность'
    )
    
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Аватар',
        validators=[validate_avatar]
    )
    
    avatar_small = models.ImageField(
        upload_to='avatars/small/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Маленький аватар (50x50)',
        editable=False
    )
    
    avatar_medium = models.ImageField(
        upload_to='avatars/medium/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Средний аватар (100x100)',
        editable=False
    )
    
    avatar_large = models.ImageField(
        upload_to='avatars/large/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Большой аватар (200x200)',
        editable=False
    )
    
    profile_slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        verbose_name='URL профиля',
        help_text='Используется для публичных ссылок на профиль'
    )
    
    profile_meta_title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Meta Title профиля'
    )
    
    profile_meta_description = models.TextField(
        blank=True,
        verbose_name='Meta Description профиля',
        max_length=300
    )
    
    profile_views = models.PositiveIntegerField(
        default=0,
        verbose_name='Просмотры профиля'
    )
    
    last_profile_update = models.DateTimeField(
        auto_now=True,
        verbose_name='Последнее обновление профиля'
    )
    
    is_verified = models.BooleanField(
        default=False,
        verbose_name='Верифицированный профиль'
    )
    
    verification_badge = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Бейдж верификации'
    )
    
    def save(self, *args, **kwargs):
        if not self.profile_slug and self.user:
            base_slug = slugify(self.user.username)
            slug = base_slug
            counter = 1
            while UserProfile.objects.filter(profile_slug=slug).exclude(user=self.user).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.profile_slug = slug
        
        if self.public_bio:
            self.public_bio = escape(self.public_bio)
        
        if self.avatar:
            try:
                self.process_avatar()
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Ошибка обработки аватара для пользователя {self.user.username}: {str(e)}')
        
        original_background = None
        if not hasattr(self, '_background_processed') and self.profile_background:
            try:
                if self.profile_background and hasattr(self.profile_background, 'file'):
                    self.process_background()
                    self._background_processed = True
                elif self.profile_background and self.profile_background.name:
                    import os
                    from django.conf import settings
                    
                    file_path = os.path.join(settings.MEDIA_ROOT, self.profile_background.name)
                    if os.path.exists(file_path):
                        self._background_processed = True
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f'Фон не удалось обработать: {str(e)}')
        if hasattr(self, '_background_processed'):
            pass
        elif self.profile_background:
            try:
                original_background = self.profile_background
                self.process_background()
                self._background_processed = True
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f'Ошибка обработки фона для пользователя {self.user.username}: {str(e)}')
                if original_background:
                    self.profile_background = original_background
        
        if not self.profile_meta_title and self.user:
            self.profile_meta_title = f"Профиль {self.user.username} | Техресурс"
        
        if not self.profile_meta_description and self.public_bio:
            clean_bio = self.public_bio[:200]
            self.profile_meta_description = f"{clean_bio}..."
        
        super().save(*args, **kwargs)

    def process_avatar(self):
        """Безопасная обработка и создание ресайзов аватара"""
        if not self.avatar:
            return
        
        try:
            if not hasattr(self.avatar, 'file') or not self.avatar.file:
                return 
                
            from io import BytesIO
            from django.core.files.base import ContentFile
            from PIL import Image as PILImage
            import os
            
            try:
                img = PILImage.open(self.avatar.file)
            except (FileNotFoundError, OSError) as e:
                logger = logging.getLogger(__name__)
                logger.error(f'Ошибка открытия аватара: {str(e)}')
                return 
            
            if img.mode in ('RGBA', 'LA', 'P'):
                background = PILImage.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode == 'LA':
                    background.paste(img, mask=img.split()[-1])
                    img = background
            
            sizes = {
                'small': (50, 50),
                'medium': (100, 100),
                'large': (200, 200)
            }
            
            for size_name, dimensions in sizes.items():
                try:
                    img_copy = img.copy()
                    img_copy.thumbnail(dimensions, PILImage.Resampling.LANCZOS)
                    
                    square_img = PILImage.new('RGB', dimensions, (255, 255, 255))
                    offset = (
                        (dimensions[0] - img_copy.size[0]) // 2,
                        (dimensions[1] - img_copy.size[1]) // 2
                    )
                    square_img.paste(img_copy, offset)
                    
                    buffer = BytesIO()
                    square_img.save(buffer, format='JPEG', quality=85, optimize=True)
                    buffer.seek(0)
                    
                    field_name = f'avatar_{size_name}'
                    filename = f"{self.user.username}_{size_name}.jpg"
                    
                    getattr(self, field_name).save(
                        filename,
                        ContentFile(buffer.read()),
                        save=False
                    )
                    buffer.close()
                except Exception as e:
                    logger = logging.getLogger(__name__)
                    logger.warning(f'Ошибка создания ресайза {size_name}: {str(e)}')
                    continue
            
            if img.size[0] > 800 or img.size[1] > 800:
                img.thumbnail((800, 800), PILImage.Resampling.LANCZOS)
            
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85, optimize=True)
            buffer.seek(0)
            
            self.avatar.save(
                f"{self.user.username}_original.jpg",
                ContentFile(buffer.read()),
                save=False
            )
            buffer.close()
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Критическая ошибка обработки аватара: {str(e)}')
            
    def process_background(self):
        """Безопасная обработка фона профиля"""
        if not self.profile_background:
            return
        
        try:
            if hasattr(self.profile_background, 'file') and self.profile_background.file:
                try:
                    from io import BytesIO
                    from django.core.files.base import ContentFile
                    from PIL import Image as PILImage
                    import time
                    import re
                    
                    self.profile_background.file.seek(0)
                    img = PILImage.open(self.profile_background.file)
                    
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = PILImage.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        if img.mode == 'RGBA':
                            background.paste(img, mask=img.split()[-1])
                            img = background
                        elif img.mode == 'LA':
                            background.paste(img, mask=img.split()[-1])
                            img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    if img.size[0] > 1920 or img.size[1] > 1080:
                        img.thumbnail((1920, 1080), PILImage.Resampling.LANCZOS)
                    
                    buffer = BytesIO()
                    img.save(buffer, format='JPEG', quality=80, optimize=True)
                    buffer.seek(0)
                    
                    timestamp = int(time.time())
                    username_clean = re.sub(r'[^\w.-]', '_', self.user.username)
                    filename = f"{username_clean}_background_{timestamp}.jpg"
                    
                    self.profile_background.save(
                        filename,
                        ContentFile(buffer.read()),
                        save=False
                    )
                    buffer.close()
                    
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f'Ошибка обработки фона для пользователя {self.user.username}: {str(e)}')
                    self.profile_background = None
                    
            elif hasattr(self.profile_background, 'name') and self.profile_background.name:
                pass
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Критическая ошибка обработки фона для пользователя {self.user.username}: {str(e)}')
            self.profile_background = None

    def get_public_tags(self):
        """Получить публичные теги для отображения"""
        if not self.profile_tags:
            return []
        
        display_names = {
            'customer': '👤 Клиент',
            'partner': '🤝 Партнер',
            'developer': '💻 Разработчик',
            'supplier': '🚚 Поставщик',
            'carrier': '📦 Перевозчик',
            'contractor': '🔧 Подрядчик',
            'investor': '💰 Инвестор',
            'employee': '👨‍💼 Сотрудник',
            'vip': '⭐ VIP клиент',
        }
        
        return [display_names.get(tag, tag) for tag in self.profile_tags]
    
    def get_absolute_url(self):
        """URL публичного профиля"""
        if self.profile_slug:
            return f"/profile/{self.profile_slug}/"
        return f"/profile/{self.user.id}/"
    
    def can_view_profile(self, request_user):
        """Проверка прав на просмотр профиля"""
        if not self.user.is_active:
            return False
        
        if request_user.is_superuser:
            return True
        
        if self.privacy_mode == 'hidden':
            return request_user == self.user or request_user.is_staff
        
        if self.privacy_mode == 'private':
            return request_user == self.user or request_user.is_staff
        
        return True
    
    def increment_views(self):
        """Увеличить счетчик просмотров"""
        self.profile_views += 1
        self.save(update_fields=['profile_views'])
    
    def get_skills_list(self):
        """Получить список навыков"""
        if not self.public_skills:
            return []
        return [skill.strip() for skill in self.public_skills.split(',')]

    def get_avatar_url(self, size='small'):
        """Безопасное получение URL аватара нужного размера"""
        import os
        
        try:
            if size == 'small' and self.avatar_small and self.avatar_small.name:
                if os.path.exists(self.avatar_small.path):
                    return self.avatar_small.url
            elif size == 'medium' and self.avatar_medium and self.avatar_medium.name:
                if os.path.exists(self.avatar_medium.path):
                    return self.avatar_medium.url
            elif size == 'large' and self.avatar_large and self.avatar_large.name:
                if os.path.exists(self.avatar_large.path):
                    return self.avatar_large.url
            elif self.avatar and self.avatar.name:
                if os.path.exists(self.avatar.path):
                    return self.avatar.url
        except (ValueError, FileNotFoundError, OSError):
            pass
        
        return None

    def has_avatar(self):
        """Проверить, есть ли рабочий аватар"""
        import os
        try:
            return bool(self.avatar and self.avatar.name and os.path.exists(self.avatar.path))
        except (ValueError, FileNotFoundError, OSError):
            return False
        
    def has_background(self):
        """Проверяет, есть ли рабочий фон"""
        if not self.profile_background or not self.profile_background.name:
            return False
        
        try:
            if hasattr(self.profile_background, 'path'):
                import os
                return os.path.exists(self.profile_background.path)
            
            if hasattr(self.profile_background, 'file') and self.profile_background.file:
                return True
                
            return False
            
        except (ValueError, FileNotFoundError, OSError, AttributeError):
            return False

    def get_background_url(self):
        """Безопасное получение URL фона"""
        try:
            if self.has_background() and self.profile_background and self.profile_background.name:
                return self.profile_background.url
        except (ValueError, AttributeError):
            pass
        return None

    def can_view_field(self, viewer, field_name):
        """
        Проверяет, может ли viewer просматривать поле field_name
        """
        if not viewer.is_authenticated:
            return False
        
        if viewer == self.user:
            return True
        
        if viewer.is_staff or viewer.is_superuser:
            return True
        
        if not self.can_view_profile(viewer):
            return False
        
        visibility_field = f'{field_name}_visibility'
        if hasattr(self, visibility_field):
            visibility = getattr(self, visibility_field)
        else:
            return self.privacy_mode == 'public'
        
        if visibility == 'public':
            return True
        elif visibility == 'registered':
            return viewer.is_authenticated
        elif visibility == 'friends':
            return viewer.is_authenticated
        elif visibility == 'private':
            return False
        
        return False

    def get_visible_fields(self, viewer):
        """
        Возвращает словарь с видимыми полями для viewer
        """
        visible = {}
        
        if self.can_view_profile(viewer):
            visible['username'] = self.user.username
            visible['name'] = f"{self.user.first_name} {self.user.last_name}".strip()
            visible['date_joined'] = self.user.date_joined
            
            fields_to_check = [
                ('email', self.user.email),
                ('phone', self.phone),
                ('company', self.company),
                ('position', self.position),
                ('public_bio', self.public_bio),
                ('public_skills', self.get_skills_list() if self.public_skills else []),
            ]
            
            for field_name, value in fields_to_check:
                if self.can_view_field(viewer, field_name):
                    visible[field_name] = value
        
        return visible

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"
        indexes = [
            models.Index(fields=['profile_slug']),
            models.Index(fields=['privacy_mode', 'is_active']),
        ]

    def __str__(self):
        return f"Профиль {self.user.username}"
    
    def age(self):
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None

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
    ip_address = models.GenericIPAddressField(verbose_name="IP-адрес", null=True)
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
    legal_address = models.TextField(verbose_name="Юридический адрес", blank=True)  
    is_legal = models.BooleanField(default=False, verbose_name="Юридическое лицо")

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


class Category(models.Model):
    """Модель категорий товаров с поддержкой вложенности"""
    name = models.CharField(max_length=200, verbose_name="Название категории")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="URL", help_text="Автоматически генерируется из названия")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                              verbose_name="Родительская категория", related_name='children')
    description = models.TextField(blank=True, verbose_name="Описание")
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name="Изображение")
    order = models.IntegerField(default=0, verbose_name="Порядок сортировки")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    seo_title = models.CharField(max_length=200, blank=True, verbose_name="SEO Title")
    seo_description = models.TextField(max_length=160, blank=True, verbose_name="SEO Description")
    seo_keywords = models.TextField(blank=True, verbose_name="SEO Keywords")
    show_in_menu = models.BooleanField(default=True, verbose_name="Показывать в меню")
    product_count = models.IntegerField(default=0, verbose_name="Количество товаров", editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['order', 'name']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent} > {self.name}"
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        
        if not self.seo_title:
            if self.parent:
                self.seo_title = f"{self.name} | {self.parent.name} | Техресурс"
            else:
                self.seo_title = f"{self.name} | Техресурс"
        
        super().save(*args, **kwargs)
        
        self.update_product_counts()
    
    def update_product_counts(self):
        """Обновляет счетчик товаров для категории и всех ее родителей"""
        from django.db.models import Count
        
        def get_all_children(category, result=None):
            if result is None:
                result = []
            result.append(category.id)
            for child in category.children.all():
                get_all_children(child, result)
            return result
        
        all_category_ids = get_all_children(self)
        
        count = Product.objects.filter(
            category__in=all_category_ids,
            is_active=True
        ).count()
        
        Category.objects.filter(id=self.id).update(product_count=count)
        
        if self.parent:
            self.parent.update_product_counts()
    
    def get_full_path(self):
        """Возвращает полный путь категории (всех родителей)"""
        path = []
        current = self
        while current:
            path.insert(0, current.name)
            current = current.parent
        return ' > '.join(path)
    
    def get_absolute_url(self):
        """URL для просмотра категории"""
        return f"/products/?category={self.slug}"
    
    def get_breadcrumbs(self):
        """Возвращает хлебные крошки для категории"""
        breadcrumbs = []
        current = self
        while current:
            breadcrumbs.insert(0, {
                'name': current.name,
                'url': f"/products/?category={current.slug}"
            })
            current = current.parent
        
        breadcrumbs.insert(0, {
            'name': 'Каталог',
            'url': '/products/'
        })
        return breadcrumbs
    
    def get_children_tree(self):
        """Возвращает дерево подкатегорий"""
        def build_tree(category):
            children = []
            for child in category.children.filter(is_active=True).order_by('order', 'name'):
                children.append({
                    'category': child,
                    'children': build_tree(child)
                })
            return children
        
        return build_tree(self)
    
    def get_active_products(self):
        """Возвращает активные товары категории и всех подкатегорий"""
        def get_all_children_ids(category, result=None):
            if result is None:
                result = []
            result.append(category.id)
            for child in category.children.all():
                get_all_children_ids(child, result)
            return result
        
        all_category_ids = get_all_children_ids(self)
        return Product.objects.filter(
            category__in=all_category_ids,
            is_active=True
        )

class Product(models.Model):
    CURRENCY_CHOICES = [
        ('RUB', '₽ Рубль'),
        ('USD', '$ Доллар США'),
        ('EUR', '€ Евро'),
    ]
    
    SYNONYMS = {
        # Оборудование
        'транспортер': ['транспортёр', 'конвейер', 'ленточный конвейер', 'рольганг', 'перемещения'],
        'шнек': ['шнековый', 'винтовой конвейер', 'шнековый транспортер', 'винтовой транспортер'],
        'насос': ['помпа', 'насосное оборудование', 'перекачивающее устройство'],
        'компрессор': ['воздушный компрессор', 'компрессорное оборудование'],
        'дробилка': ['измельчитель', 'мельница', 'дробильное оборудование', 'дробильная установка'],
        'смеситель': ['миксер', 'мешалка', 'смесительное оборудование'],
        'фильтр': ['фильтрующее устройство', 'очиститель', 'фильтрационное оборудование'],
        'сушилка': ['сушильное оборудование', 'сушильная установка', 'сушильный аппарат'],
        'клапан': ['вентиль', 'задвижка', 'запорная арматура', 'регулирующий клапан'],
        'датчик': ['сенсор', 'измерительный прибор', 'контроллер', 'преобразователь'],
        'привод': ['электропривод', 'приводное устройство', 'мотор-редуктор'],
        
        # Действия
        'купить': ['приобрести', 'заказать', 'оформить заказ', 'купить недорого', 'цена', 'стоимость'],
        'продажа': ['реализация', 'поставка', 'продажа оборудования'],
        
        # Категории
        'промышленный': ['индустриальный', 'производственный', 'промышленное'],
        'автоматизация': ['автоматика', 'АСУ ТП', 'системы управления', 'SCADA', 'контроллеры'],
        'электрика': ['электрооборудование', 'электротехника', 'электрическое оборудование'],
        
        # Характеристики
        'нержавеющий': ['нержавейка', 'коррозионностойкий', 'inox', 'stainless steel'],
        'чугунный': ['чугун', 'литье чугуна'],
        'стальной': ['сталь', 'металлический'],
        
        # Состояния
        'новый': ['новое оборудование', 'оригинал', 'новье'],
        'б/у': ['бу', 'подержанный', 'восстановленный', 'после капремонта'],
    }
    
    # Общие ключевые слова для всех товаров
    COMMON_KEYWORDS = [
        'промышленное оборудование',
        'производственное оборудование',
        'техническое оснащение',
        'купить оборудование',
        'оборудование цена',
        'поставка оборудования',
        'промышленная автоматизация',
        'КИПиА',
        'контрольно-измерительные приборы',
        'АСУ ТП',
        'системы управления',
        'электропривод',
        'пневматика',
        'гидравлика',
    ]
    
    name = models.CharField(max_length=200, verbose_name="Название")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='RUB',
        verbose_name="Валюта цены",
        help_text="Валюта, в которой указана цена товара"
    )
    price_in_rub = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Цена в рублях",
        editable=True,
        default=0
    )
    last_rate_update = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Последнее обновление курса",
        editable=True
    )
    description = models.TextField(verbose_name="Описание", blank=True)
    quantity = models.IntegerField(default=0, verbose_name="Остаток")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, 
                             verbose_name="Категория", related_name='products')
    article = models.CharField(max_length=15, verbose_name="Артикул", blank=True, unique=True, editable=False, help_text="Автоматически генерируется при создании")
    image = models.ImageField(upload_to='products/', verbose_name="Изображение", blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="Активный")
    seo_title = models.CharField(max_length=200, verbose_name="SEO Title",blank=True,help_text="Автоматически генерируется")
    seo_description = models.TextField(verbose_name="SEO Description", max_length=160,blank=True,help_text="Автоматически генерируется")
    seo_keywords = models.TextField(verbose_name="SEO Keywords",blank=True,help_text="Автоматически генерируется")
    slug = models.SlugField(max_length=200,unique=True,blank=True,verbose_name="URL",help_text="Автоматически генерируется из названия")
    
    brand = models.CharField(max_length=100, verbose_name="Бренд", blank=True, help_text="Например: ABB, Schneider Electric, Siemens")
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name="Рейтинг")
    popularity = models.IntegerField(default=0, verbose_name="Популярность")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="Вес", help_text="Вес в килограммах. Пример: 2.5")
    dimensions = models.CharField(max_length=50, blank=True, verbose_name="Габариты", help_text="Формат: Длина×Ширина×Высота в см. Пример: 10×20×5")
    material = models.CharField(max_length=100, blank=True, verbose_name="Материал", help_text="Например: пластик, сталь, алюминий, комбинированный")
    warranty = models.IntegerField(default=12, verbose_name="Гарантия (мес)", help_text="Срок гарантии в месяцах. Стандартно 12 месяцев")

    vat_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('22.00'),  
        verbose_name="Ставка НДС (%)"
    )
    is_fragile = models.BooleanField(default=False, verbose_name="Хрупкий товар")
    requires_special_delivery = models.BooleanField(default=False, verbose_name="Требует спецдоставки")

    
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    last_restock = models.DateTimeField(null=True, blank=True, verbose_name="Последнее пополнение")

    specifications = models.JSONField(default=dict, blank=True, verbose_name="Характеристики", help_text="Дополнительные характеристики в формате JSON. Пример: {'Мощность': '100W', 'Напряжение': '220V'}")
        
    def save(self, *args, **kwargs):
        self.calculate_price_in_rub()
    
        if self.price and self.vat_rate:
            hundred = Decimal('100')
            self.price_without_vat = self.price / (1 + self.vat_rate / hundred)
    
        is_new = not self.pk
    
        # 1. Сначала генерируем артикул для новых товаров
        if is_new or not self.article or self.article == '':
            self.article = self.generate_article()
    
        # 2. Проверяем, нужно ли обновить SEO поля
        need_seo_update = (
            is_new or  # Новый товар
            not self.seo_title or  # Отсутствует заголовок
            not self.seo_description or  # Отсутствует описание
            not self.seo_keywords or  # Отсутствуют ключевые слова
            self._has_name_changed() or  # Изменилось название
            self._has_price_changed() or  # Изменилась цена
            self._has_brand_changed() or  # Изменился бренд
            self._has_category_changed()  # Изменилась категория
        )
        
        if need_seo_update:
            self.generate_seo_fields()
    
        if is_new or not self.slug or self.slug == '':
            if self.name:
                self.slug = self.generate_seo_slug()
    
        self.updated_at = datetime.now()
    
        super().save(*args, **kwargs)
        
    def get_absolute_url(self):
        """Возвращает SEO-дружественный URL товара"""
        from django.urls import reverse
        return reverse('product_detail', kwargs={'slug': self.slug})

    def get_display_price(self, target_currency='RUB'):
        """Получение цены в указанной валюте"""
        from .models import CurrencyRate
        
        if target_currency == self.currency:
            return self.price
        
        if target_currency == 'RUB':
            return self.price_in_rub
        
        try:
            rate = CurrencyRate.get_rate(target_currency)
            if rate == 0:
                return self.price_in_rub
            
            price_in_target = self.price_in_rub / rate
            return price_in_target.quantize(Decimal('0.01'))
        except Exception as e:
            return self.price_in_rub

    def _has_name_changed(self):
        """Проверяет, изменилось ли название товара"""
        if not self.pk:
            return False
        try:
            old = Product.objects.get(pk=self.pk)
            return old.name != self.name
        except Product.DoesNotExist:
            return False
    
    def get_price_for_user(self, user, quantity=1):
        """Получить цену для конкретного пользователя с учетом всех скидок"""
        from django.core.cache import cache
        
        # Базовая цена в рублях (используем существующий метод)
        base_price = self.get_display_price('RUB')
        
        if not user or not user.is_authenticated:
            return base_price
        
        try:
            user_profile = user.userprofile
        except UserProfile.DoesNotExist:
            return base_price
    
        if hasattr(user, 'price_contracts'):
            active_contract = user.price_contracts.filter(
                is_active=True, 
                valid_from__lte=timezone.now().date(),
                valid_to__gte=timezone.now().date()
            ).first()
            
            if active_contract and str(self.id) in active_contract.special_prices:
                return Decimal(str(active_contract.special_prices[str(self.id)]))
        
        if hasattr(user, 'discount') and user.discount and user.discount.is_active:
            applicable = True
            if hasattr(user.discount, 'applicable_categories') and user.discount.applicable_categories.exists():
                if self.category not in user.discount.applicable_categories.all():
                    applicable = False
            
            if applicable:
                discounted_price = user.discount.apply_to_price(base_price)
                return discounted_price
        
        volume_discount = self.get_volume_discount(quantity)
        if volume_discount:
            return base_price * (100 - volume_discount) / 100
        
        return base_price

    def get_volume_discount(self, quantity):
        """Скидка от количества"""
        discounts = {
            5: 2,   # от 5 шт - 2%
            10: 3,  # от 10 шт - 3%
            25: 4,
            50: 5,
            100: 7,
        }
        for min_qty, discount in sorted(discounts.items(), reverse=True):
            if quantity >= min_qty:
                return discount
        return 0

    def _has_price_changed(self):
        """Проверяет, изменилась ли цена товара"""
        if not self.pk:
            return False
        try:
            old = Product.objects.get(pk=self.pk)
            return old.price != self.price or old.currency != self.currency
        except Product.DoesNotExist:
            return False
    
    def _has_brand_changed(self):
        """Проверяет, изменился ли бренд"""
        if not self.pk:
            return False
        try:
            old = Product.objects.get(pk=self.pk)
            return old.brand != self.brand
        except Product.DoesNotExist:
            return False
    
    def _has_category_changed(self):
        """Проверяет, изменилась ли категория"""
        if not self.pk:
            return False
        try:
            old = Product.objects.get(pk=self.pk)
            return old.category_id != self.category_id
        except Product.DoesNotExist:
            return False
            
    def __str__(self):
        return f"{self.name} (арт: {self.article})"
    
    def get_main_image(self):
        """Возвращает основное изображение товара"""
        main_image = self.images.filter(is_main=True).first()
        if main_image:
            return main_image
        first_image = self.images.first()
        if first_image:
            return first_image
        return None
    
    def calculate_price_in_rub(self):
        """Рассчитывает цену в рублях по текущему курсу"""
        try:
            from .models import CurrencyRate 
            
            if self.currency == 'RUB':
                self.price_in_rub = self.price
            else:
                rate = CurrencyRate.get_rate(self.currency)
                self.price_in_rub = self.price * rate
                self.last_rate_update = timezone.now()
            
            self.price_in_rub = self.price_in_rub.quantize(Decimal('0.01'))
            
        except Exception as e:
            if not self.pk:
                self.price_in_rub = self.price
    
    def update_price_from_currency(self):
        """Обновляет цену в рублях по текущему курсу"""
        from .models import CurrencyRate
        
        try:
            if self.currency != 'RUB':
                rate = CurrencyRate.get_rate(self.currency)
                old_price_rub = self.price_in_rub
                self.price_in_rub = self.price * rate
                self.last_rate_update = timezone.now()
                self.price_in_rub = self.price_in_rub.quantize(Decimal('0.01'))
                self.save(update_fields=['price_in_rub', 'last_rate_update'])
                return True
        except Exception as e:
            print(f"Ошибка обновления цены для товара {self.article}: {str(e)}")
        
        return False
    
    def get_price_with_currency_symbol(self):
        """Получение цены с символом валюты"""
        currency_symbols = {
            'RUB': '₽',
            'USD': '$',
            'EUR': '€',
        }
        symbol = currency_symbols.get(self.currency, '₽')
        
        price_str = f"{self.price:,.2f}".replace(',', ' ').replace('.', ',')
        return f"{price_str} {symbol}"

    def get_price_in_rub_with_symbol(self):
        """Получение цены в рублях с символом"""
        price_str = f"{self.price_in_rub:,.2f}".replace(',', ' ').replace('.', ',')
        return f"{price_str} ₽"
    
    @property
    def display_price(self):
        """Свойство для получения цены в рублях (для обратной совместимости)"""
        return self.price_in_rub
    
    def get_images_count(self):
        """Возвращает количество изображений товара"""
        return self.images.count()
    
    def get_images(self):
        """Возвращает все изображения товара в правильном порядке"""
        return self.images.all().order_by('order', 'created_at')
    
    def generate_article(self):
        """
        Генерация артикула по формату: ДДММГГПП
        Где:
          ДД - день месяца (01-31)
          ММ - месяц (01-12)
          ГГ - две последние цифры года (24 для 2024)
          ПП - порядковый номер товара за этот день (01-99)
        """
        now = datetime.now()
        
        day_str = f"{now.day:02d}"       
        month_str = f"{now.month:02d}"   
        year_str = f"{now.year % 100:02d}"  
        
        date_part = f"{day_str}{month_str}{year_str}"
        
        today = date.today()
        today_products = Product.objects.filter(
            created_at__date=today
        )
        
        if today_products.exists():
            max_order = 0
            for product in today_products:
                if product.article:
                    try:
                        current_order = int(product.article[-2:])
                        if current_order > max_order:
                            max_order = current_order
                    except (ValueError, IndexError):
                        continue
            
            next_order = max_order + 1
            
            if next_order > 99:
                tomorrow = now.replace(day=now.day + 1)
                day_str = f"{tomorrow.day:02d}"
                month_str = f"{tomorrow.month:02d}"
                year_str = f"{tomorrow.year % 100:02d}"
                date_part = f"{day_str}{month_str}{year_str}"
                next_order = 1
        else:
            next_order = 1
        
        order_str = f"{next_order:02d}"  
        
        return f"{date_part}{order_str}"
    
    def generate_seo_fields(self):
        """Автоматическая генерация SEO полей с учетом синонимов"""
        if not self.name:
            return
        
        # 1. Генерация SEO заголовка
        self.seo_title = self._generate_seo_title()
        
        # 2. Генерация SEO описания
        self.seo_description = self._generate_seo_description()
        
        # 3. Генерация ключевых слов с синонимами
        self.seo_keywords = self._generate_seo_keywords()
    
    def _generate_seo_title(self):
        """Генерирует SEO заголовок с учетом разных форм"""
        title_parts = []
        
        # Добавляем бренд если есть
        if self.brand:
            title_parts.append(self.brand)
        
        # Основное название
        title_parts.append(self.name)
        
        # Добавляем альтернативные названия для заголовка (если есть синонимы)
        alt_names = self._get_synonyms_for_product()
        if alt_names:
            title_parts.append(f"({alt_names[0]})")
        
        # Добавляем цену
        if self.price:
            title_parts.append(self.get_price_with_currency_symbol())
        
        # Добавляем ключевое действие
        if self.category:
            title_parts.append(f"купить {self.category.name.lower()}")
        else:
            title_parts.append("купить промышленное оборудование")
        
        # Добавляем название компании
        title_parts.append("Техресурс")
        
        # Собираем заголовок
        title = " - ".join(title_parts)
        
        # Обрезаем до 200 символов, стараясь не резать на полуслове
        if len(title) > 200:
            title = title[:197] + "..."
        
        return title
    
    def _generate_seo_description(self):
        """Генерирует SEO описание с синонимами и ключевыми фразами"""
        desc_parts = []
        
        # Основная информация о товаре
        desc_parts.append(f"{self.name}")
        
        # Добавляем синонимы в скобках
        synonyms = self._get_synonyms_for_product()
        if synonyms:
            desc_parts.append(f"(также: {', '.join(synonyms[:3])})")
        
        # Ценовая информация
        if self.price:
            price_text = f"по цене {self.get_price_with_currency_symbol()}"
            desc_parts.append(price_text)
        
        # Технические характеристики
        tech_info = []
        if self.brand:
            tech_info.append(f"бренд {self.brand}")
        if self.article:
            tech_info.append(f"артикул {self.article}")
        if self.material:
            tech_info.append(f"материал {self.material}")
        if self.weight:
            tech_info.append(f"вес {self.weight} кг")
        
        if tech_info:
            desc_parts.append(f"характеристики: {', '.join(tech_info)}")
        
        # Категория и применение
        if self.category:
            desc_parts.append(f"категория {self.category.name}")
            
            # Добавляем фразы для конкретной категории
            if "насос" in self.category.name.lower():
                desc_parts.append("перекачка жидкостей, водоснабжение")
            elif "конвейер" in self.category.name.lower() or "транспортер" in self.category.name.lower():
                desc_parts.append("перемещение грузов, транспортировка материалов")
            elif "дробилка" in self.category.name.lower():
                desc_parts.append("измельчение материалов, дробление пород")
        
        # Добавляем описание из карточки товара
        if self.description:
            clean_desc = re.sub(r'<[^>]+>', '', self.description)
            clean_desc = ' '.join(clean_desc.split()[:15])  # Первые 15 слов
            if clean_desc:
                desc_parts.append(clean_desc + "...")
        
        # Добавляем призыв к действию
        desc_parts.append("Звоните! Доставка по РФ.")
        
        # Собираем описание
        description = ". ".join(desc_parts)
        
        # Обрезаем до 160 символов, стараясь не резать на полуслове
        if len(description) > 160:
            description = description[:157] + "..."
        
        return description
    
    def _generate_seo_keywords(self):
        """Генерирует ключевые слова с учетом синонимов и N-грамм"""
        keywords = set()
        
        # 1. Добавляем название товара и его части
        name_lower = self.name.lower()
        keywords.add(name_lower)
        
        # Разбиваем название на слова
        name_words = re.findall(r'\w+', name_lower)
        keywords.update(name_words)
        
        # Добавляем биграммы (пары слов)
        if len(name_words) > 1:
            bigrams = [f"{name_words[i]} {name_words[i+1]}" for i in range(len(name_words)-1)]
            keywords.update(bigrams)
        
        # 2. Добавляем синонимы
        synonyms = self._get_all_synonyms(name_lower)
        keywords.update(synonyms)
        
        # 3. Добавляем поисковые фразы с синонимами
        search_phrases = ['купить', 'цена', 'продажа', 'стоимость']
        for word in name_words:
            for phrase in search_phrases:
                keywords.add(f"{phrase} {word}")
                # Добавляем фразы с синонимами
                for syn in synonyms:
                    if len(syn.split()) <= 2:  # Только короткие синонимы
                        keywords.add(f"{phrase} {syn}")
        
        # 4. Добавляем информацию о категории
        if self.category:
            cat_lower = self.category.name.lower()
            keywords.add(cat_lower)
            keywords.add(f"купить {cat_lower}")
            keywords.add(f"{cat_lower} цена")
            
            # Добавляем родительские категории
            parent = self.category.parent
            while parent:
                parent_lower = parent.name.lower()
                keywords.add(parent_lower)
                keywords.add(f"купить {parent_lower}")
                parent = parent.parent
        
        # 5. Добавляем бренд и его вариации
        if self.brand:
            brand_lower = self.brand.lower()
            keywords.add(brand_lower)
            keywords.add(f"{brand_lower} оборудование")
            keywords.add(f"{brand_lower} купить")
        
        # 6. Добавляем характеристики
        if self.material:
            material_lower = self.material.lower()
            keywords.add(material_lower)
            keywords.add(f"{material_lower} {name_lower}")
        
        # 7. Добавляем общие ключевые слова из COMMON_KEYWORDS
        keywords.update(self.COMMON_KEYWORDS)
        
        # 8. Добавляем специфичные для отрасли ключи на основе названия
        industry_keywords = self._get_industry_keywords(name_lower)
        keywords.update(industry_keywords)
        
        # Преобразуем в список, сортируем и ограничиваем
        keywords_list = list(keywords)
        keywords_list.sort()  # Сортируем для консистентности
        
        # Ограничиваем количество (но оставляем больше, так как это keywords)
        return ', '.join(keywords_list[:25])
    
    def _get_synonyms_for_product(self):
        """Возвращает список синонимов для данного товара"""
        if not self.name:
            return []
        
        name_lower = self.name.lower()
        found_synonyms = set()
        
        for key, syn_list in self.SYNONYMS.items():
            # Проверяем, содержится ли ключевое слово в названии
            if key in name_lower:
                found_synonyms.update(syn_list)
            
            # Проверяем, содержится ли синоним в названии (обратный поиск)
            for syn in syn_list:
                if syn in name_lower:
                    found_synonyms.add(key)
                    break
        
        # Убираем слишком длинные синонимы
        return [s for s in found_synonyms if len(s.split()) <= 3][:5]
    
    def _get_all_synonyms(self, text):
        """Возвращает все синонимы для текста"""
        synonyms = set()
        
        for key, syn_list in self.SYNONYMS.items():
            if key in text:
                synonyms.update(syn_list)
            for syn in syn_list:
                if syn in text:
                    synonyms.add(key)
        
        return synonyms
        
    def generate_seo_slug(self):
        """Генерирует SEO-оптимизированный slug с ключевыми словами"""
        if not self.name:
            return ''
        
        # Берем название
        base = self.name.lower()
        
        # Добавляем ключевое слово из категории
        if self.category:
            category_keywords = {
                'насос': 'pump',
                'компрессор': 'compressor',
                'дробилка': 'crusher',
                'конвейер': 'conveyor',
                'транспортер': 'conveyor',
                'шнек': 'auger',
                'смеситель': 'mixer',
                'фильтр': 'filter',
            }
            
            for ru, en in category_keywords.items():
                if ru in base:
                    base = f"{base}-{en}"
                    break
        
        # Транслитерируем и создаем slug
        slug = slugify(base)
        
        # Добавляем артикул для уникальности
        if self.article:
            slug = f"{slug}-{self.article}"
        
        return slug[:200]  # Ограничиваем длину
    
    def _get_industry_keywords(self, product_name):
        """Возвращает отраслевые ключевые слова на основе названия товара"""
        industry_keywords = set()
        
        # Словарь отраслевых привязок
        industry_map = {
            'нефть': ['нефтегазовая отрасль', 'нефтепереработка', 'нефтепромысел'],
            'газ': ['газовая промышленность', 'газодобыча', 'газотранспортная система'],
            'хим': ['химическая промышленность', 'химическое производство'],
            'пищев': ['пищевая промышленность', 'пищевое производство'],
            'цемент': ['цементная промышленность', 'стройматериалы', 'производство цемента'],
            'металл': ['металлургия', 'металлообработка', 'металлургическая промышленность'],
            'горн': ['горная промышленность', 'горнодобыча', 'горнорудная отрасль'],
            'энерг': ['энергетика', 'электроэнергетика'],
            'вод': ['водоснабжение', 'водоподготовка', 'водоотведение'],
        }
        
        for key, industries in industry_map.items():
            if key in product_name:
                industry_keywords.update(industries)
        
        return industry_keywords
    
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
    
    def get_article_date(self):
        """Получить дату из артикула для отображения"""
        if len(self.article) == 8:
            try:
                day = int(self.article[0:2])
                month = int(self.article[2:4])
                year = 2000 + int(self.article[4:6])  # 20 + ГГ
                return f"{day:02d}.{month:02d}.{year}"
            except (ValueError, IndexError):
                return "Дата неизвестна"
        return "Дата неизвестна"

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['article']),
            models.Index(fields=['is_active', 'category']),
            models.Index(fields=['price', 'is_active']),
            models.Index(fields=['slug']),
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
        """Общая стоимость корзины в рублях"""
        total = Decimal('0')
        for item in self.cartitem_set.all():
            total += item.get_total_price() 
        return total
    
    def get_items_count(self):
        return self.cartitem_set.count()
    
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
        """Возвращает сумму в рублях с учетом конвертации валюты"""
        price_in_rub = self.product.get_display_price('RUB')
        return price_in_rub * self.quantity
    
    def get_unit_price_in_rub(self):
        """Возвращает цену за единицу в рублях"""
        return self.product.get_display_price('RUB')

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

    # PAYMENT_SYSTEMS = [
    #     ('', 'Не используется'), 
    # ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь",null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Общая сумма")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='card', verbose_name="Способ оплаты")
    customer_name = models.CharField(max_length=100, verbose_name="Контактное лицо") 
    company_name = models.CharField(max_length=200, verbose_name="Название компании", blank=True) 
    customer_phone = models.CharField(max_length=20, verbose_name="Телефон")
    customer_email = models.EmailField(verbose_name="Email")
    delivery_address = models.TextField(verbose_name="Адрес доставки")
    legal_address = models.TextField(verbose_name="Юридический адрес", blank=True)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=22.00,  verbose_name="Ставка НДС (%)")
    price_without_vat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена без НДС", help_text="Рассчитывается автоматически")
    status_changed_at = models.DateTimeField(auto_now=True, verbose_name="Время изменения статуса")
    tracking_number = models.CharField(max_length=100, blank=True, verbose_name="Трек-номер")
    shipping_company = models.CharField(max_length=100, blank=True, verbose_name="Служба доставки")
    estimated_delivery = models.DateField(null=True, blank=True, verbose_name="Примерная дата доставки")
    payment_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Комиссия платежной системы")
    delivery_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Стоимость доставки")
    final_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Итоговая сумма с учетом доставки и комиссий")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата оплаты")
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата отмены")
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
    invoice_number = models.CharField(
        'Номер счета',
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        help_text="Автоматически генерируется при создании счета"
    )
    
    invoice_date = models.DateField(
        'Дата счета',
        blank=True,
        null=True,
        help_text="Дата выставления счета"
    )
    
    customer_inn = models.CharField(
        'ИНН покупателя',
        max_length=12,
        blank=True,
        null=True,
        help_text="Для юридических лиц"
    )
    
    customer_kpp = models.CharField(
        'КПП покупателя',
        max_length=9,
        blank=True,
        null=True,
        help_text="Для юридических лиц"
    )
    
    invoice_sent = models.BooleanField(
        'Счет отправлен',
        default=False,
        help_text="Счет отправлен на email покупателя"
    )
    
    invoice_sent_at = models.DateTimeField(
        'Время отправки счета',
        blank=True,
        null=True
    )

    original_total = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="Сумма без скидки"
    )
    
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="Сумма скидки"
    )
    
    discount_percent = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        verbose_name="Процент скидки"
    )
    
    def generate_invoice_number(self):
        """Генерация номера счета без сохранения"""
        if self.invoice_number:
            return self.invoice_number
        
        from django.db import transaction
    
        with transaction.atomic():
            last_invoice = Order.objects.select_for_update().filter(
                invoice_number__isnull=False
            ).order_by('-invoice_number').first()

        today = timezone.now()
        prefix = "СЧ"
        year = today.strftime('%Y')
        month = today.strftime('%m')
        
        last_invoice = Order.objects.filter(
            invoice_number__startswith=f"{prefix}-{year}-{month}-"
        ).order_by('-invoice_number').first()
        
        if last_invoice and last_invoice.invoice_number:
            try:
                last_num = int(last_invoice.invoice_number.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
        
        return f"{prefix}-{year}-{month}-{next_num:04d}"
    
    def get_due_date(self):
        """Получить дату оплаты (срок - 5 банковских дней)"""
        if self.invoice_date:
            from datetime import timedelta
            due_date = self.invoice_date
            added_days = 0
            while added_days < 5:
                due_date += timedelta(days=1)
                if due_date.weekday() < 5:  
                    added_days += 1
            return due_date
        return None

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
            self.net_revenue = self.total_price  
            self.is_payment_finalized = True
            self.paid_at = timezone.now()
            self.save()
    
    def get_clean_revenue(self):
        """Возвращает чистую выручку"""
        return self.net_revenue if self.is_payment_finalized else 0
    
    def reduce_product_quantities(self):
        """Уменьшает количество товаров на складе"""
        for item in self.orderitem_set.all():
            if item.product.quantity >= item.quantity:
                item.product.quantity -= item.quantity
                item.product.save()
            else:
                raise ValueError(f'Недостаточно товара "{item.product.name}" на складе')
            
    def restore_product_quantities(self):
        """Возвращает товары на склад (при отмене)"""
        for item in self.orderitem_set.all():
            item.product.quantity += item.quantity
            item.product.save()

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
        """Можно отменить заказ в течение 5 минут после создания или оплаты"""
        if self.status in ['pending', 'processing']:
            time_since_creation = (timezone.now() - self.created_at).total_seconds()
            return time_since_creation < 600 
        
        if self.status == 'paid' and self.paid_at:
            time_since_payment = (timezone.now() - self.paid_at).total_seconds()
            return time_since_payment < 600 
        
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
        default=Decimal('22.00'),  # Используем Decimal
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
        if self.price and self.quantity and self.vat_rate:
            hundred = Decimal('100')
            total = self.price * self.quantity
            self.vat_amount = total * (self.vat_rate / hundred) / (1 + self.vat_rate / hundred)
            self.price_without_vat = self.price / (1 + self.vat_rate / hundred)
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
            base_url = f"/services/{self.static_service}/"
            if self.page_type == 'instruction' and self.parent:
                return f"{base_url}instructions/{self.slug}/"
            elif self.parent:
                return f"{base_url}{self.slug}/"
            else:
                return base_url
        else:
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
        
        dynamic_services = cls.objects.filter(
            page_type='main_service',
            static_service='',  
            is_active=True,
            show_in_navigation=True
        ).order_by('order')
        
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
    
class InvoiceRegistry(models.Model):
    """Реестр всех счетов для учета"""
    STATUS_CHOICES = [
        ('created', 'Создан'),
        ('sent', 'Отправлен'),
        ('paid', 'Оплачен'),
        ('overdue', 'Просрочен'),
        ('cancelled', 'Отменен'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="Заказ", related_name='invoice_registry')
    invoice_number = models.CharField(max_length=50, verbose_name="Номер счета", unique=True)
    invoice_date = models.DateField(verbose_name="Дата счета")
    due_date = models.DateField(verbose_name="Срок оплаты")
    customer_name = models.CharField(max_length=200, verbose_name="Покупатель")
    customer_inn = models.CharField(max_length=12, verbose_name="ИНН покупателя", blank=True, null=True)
    customer_email = models.EmailField(verbose_name="Email покупателя")
    customer_phone = models.CharField(max_length=20, verbose_name="Телефон покупателя")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма счета")
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма НДС")
    amount_without_vat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма без НДС")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created', verbose_name="Статус счета")
    email_sent = models.BooleanField(default=False, verbose_name="Email отправлен")
    email_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Email отправлен в")
    telegram_sent = models.BooleanField(default=False, verbose_name="Telegram отправлен")
    telegram_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Telegram отправлен в")
    admin_notes = models.TextField(blank=True, verbose_name="Заметки администратора")
    payment_details = models.JSONField(default=dict, blank=True, verbose_name="Детали оплаты")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания записи")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        verbose_name = "Реестр счетов"
        verbose_name_plural = "Реестр счетов"
        ordering = ['-invoice_date', '-created_at']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['customer_name', 'invoice_date']),
        ]
    
    def __str__(self):
        return f"Счет №{self.invoice_number} - {self.customer_name} - {self.amount} руб."
    
    def is_overdue(self):
        """Проверка просрочки"""
        from datetime import date
        return self.status != 'paid' and self.due_date < date.today()
    
    def get_overdue_days(self):
        """Количество дней просрочки"""
        from datetime import date
        if self.is_overdue():
            return (date.today() - self.due_date).days
        return 0
    
    def get_order_info(self):
        """Информация о заказе"""
        return {
            'order_id': self.order.id,
            'items': list(self.order.orderitem_set.all().values_list('product__name', 'quantity')),
            'total_items': self.order.orderitem_set.count(),
        }
    
@receiver(post_save, sender=Order)
def create_invoice_registry_entry(sender, instance, created, **kwargs):
    """Автоматическое создание записи в реестре при создании заказа"""
    from datetime import date
    from django.utils import timezone
    
    try:
        if created:
            if not instance.invoice_number:
                instance.invoice_number = instance.generate_invoice_number()
                instance.save(update_fields=['invoice_number'])
            
            InvoiceRegistry.objects.create(
                order=instance,
                invoice_number=instance.invoice_number,
                invoice_date=instance.invoice_date or date.today(),
                due_date=instance.get_due_date() or date.today(),
                customer_name=instance.customer_name,
                customer_inn=instance.customer_inn,
                customer_email=instance.customer_email,
                customer_phone=instance.customer_phone,
                amount=instance.total_price,
                vat_amount=instance.vat_amount,
                amount_without_vat=instance.price_without_vat,
                email_sent=instance.invoice_sent,
                email_sent_at=instance.invoice_sent_at,
                telegram_sent=getattr(instance, 'invoice_pdf_sent_to_telegram', False),
                telegram_sent_at=instance.invoice_sent_at if getattr(instance, 'invoice_pdf_sent_to_telegram', False) else None,
                status='created'
            )
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Ошибка создания записи реестра: {str(e)}')

@receiver(post_save, sender=Order)
def update_invoice_registry_entry(sender, instance, **kwargs):
    """Обновление записи реестра при изменении заказа"""
    if instance.invoice_number:
        try:
            registry_entry = InvoiceRegistry.objects.get(order=instance)
            registry_entry.status = 'paid' if instance.status == 'paid' else registry_entry.status
            registry_entry.email_sent = instance.invoice_sent
            registry_entry.email_sent_at = instance.invoice_sent_at
            registry_entry.save()
        except InvoiceRegistry.DoesNotExist:
            pass

class PrivacyRequest(models.Model):
    """Модель для хранения запросов по персональным данным"""
    
    REQUEST_TYPES = [
        ('access', 'Запрос о предоставлении сведений об обработке ПД'),
        ('correction', 'Требование об уточнении персональных данных'),
        ('blocking', 'Требование о блокировании персональных данных'),
        ('destruction', 'Требование об уничтожении персональных данных'),
        ('withdraw_consent', 'Отзыв согласия на обработку персональных данных'),
        ('objection', 'Возражение против обработки персональных данных'),
        ('complaint', 'Жалоба на обработку персональных данных'),
    ]
    
    STATUS_CHOICES = [
        ('received', 'Получен'),
        ('in_progress', 'В обработке'),
        ('waiting_verification', 'Ожидает верификации'),
        ('completed', 'Выполнен'),
        ('rejected', 'Отклонен'),
        ('cancelled', 'Отменен'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='privacy_requests')
    incoming_number = models.CharField(max_length=100, blank=True, verbose_name='Входящий номер')
    deadline = models.DateField(null=True, blank=True, verbose_name='Срок рассмотрения')
    # Данные запроса
    full_name = models.CharField(max_length=255, verbose_name='ФИО')
    email = models.EmailField(verbose_name='Email для связи')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    request_type = models.CharField(max_length=50, choices=REQUEST_TYPES, verbose_name='Тип запроса')
    description = models.TextField(verbose_name='Описание запроса')
    preferred_response = models.CharField(max_length=20, default='email', 
                                         choices=[('email', 'Email'), ('phone', 'Телефон'), ('post', 'Почта')],
                                         verbose_name='Предпочтительный способ ответа')
    
    # Файлы
    verification_document = models.FileField(upload_to='privacy_requests/verification/%Y/%m/', 
                                           null=True, blank=True, 
                                           verbose_name='Документ для верификации')
    
    # Системная информация
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='received', verbose_name='Статус')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP-адрес')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    
    # Даты
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата решения')
    
    # Ответ оператора
    response_text = models.TextField(blank=True, verbose_name='Текст ответа')
    response_sent_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата отправки ответа')
    response_method = models.CharField(max_length=20, blank=True, 
                                      choices=[('email', 'Email'), ('phone', 'Телефон'), ('post', 'Почта')],
                                      verbose_name='Способ отправки ответа')
    
    # Логи
    notes = models.TextField(blank=True, verbose_name='Внутренние заметки')
    
    class Meta:
        verbose_name = 'Запрос по персональным данным'
        verbose_name_plural = 'Запросы по персональным данным'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Запрос ПД #{self.id} - {self.full_name} - {self.get_request_type_display()}"
    
    def get_absolute_url(self):
        return reverse('admin_privacy_request_detail', args=[str(self.id)])
    
    @property
    def days_since_creation(self):
        """Количество дней с момента создания запроса"""
        from django.utils import timezone
        delta = timezone.now() - self.created_at
        return delta.days
    
    def can_be_processed(self):
        """Можно ли обрабатывать запрос (не истекли сроки)"""
        return self.days_since_creation <= 30 and self.status in ['received', 'in_progress']
    
    def mark_as_resolved(self, response_text, response_method):
        """Отметить запрос как решенный"""
        from django.utils import timezone
        self.status = 'completed'
        self.response_text = response_text
        self.response_method = response_method
        self.response_sent_at = timezone.now()
        self.resolved_at = timezone.now()
        self.save()

class PrivacyRequestLog(models.Model):
    """Журнал обработки запросов ПД"""
    request = models.ForeignKey(PrivacyRequest, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)  # 'received', 'verified', 'replied', etc.
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict)

class DataProtectionOfficer(models.Model):
    """Ответственный за обработку ПД"""
    full_name = models.CharField(max_length=255, verbose_name='ФИО')
    position = models.CharField(max_length=255, verbose_name='Должность')
    email = models.EmailField(verbose_name='Email')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    appointment_date = models.DateField(verbose_name='Дата назначения')
    appointment_order = models.CharField(max_length=100, verbose_name='Номер приказа')
    is_active = models.BooleanField(default=True, verbose_name='Действующий')
    
    class Meta:
        verbose_name = 'Ответственный за ПД'
        verbose_name_plural = 'Ответственные за ПД'
    
    def __str__(self):
        return f"{self.full_name} ({self.position})"
    
class ProcessingRegister(models.Model):
    """Реестр обработки ПД (требование ст. 18.1 152-ФЗ)"""
    
    PROCESSING_TYPES = [
        ('automated', 'Автоматизированная'),
        ('manual', 'Неавтоматизированная'),
        ('mixed', 'Смешанная'),
    ]
    
    STORAGE_TYPES = [
        ('electronic', 'Электронный'),
        ('paper', 'Бумажный'),
        ('mixed', 'Смешанный'),
    ]
    
    name = models.CharField(max_length=500, verbose_name='Наименование обработки')
    purpose = models.TextField(verbose_name='Цель обработки')
    categories = models.TextField(verbose_name='Категории субъектов ПД')
    data_categories = models.TextField(verbose_name='Категории ПД')
    legal_basis = models.TextField(verbose_name='Правовое основание')
    processing_type = models.CharField(max_length=20, choices=PROCESSING_TYPES, 
                                      verbose_name='Тип обработки')
    storage_type = models.CharField(max_length=20, choices=STORAGE_TYPES, 
                                   verbose_name='Форма хранения')
    retention_period = models.CharField(max_length=100, verbose_name='Срок хранения')
    destruction_procedure = models.TextField(verbose_name='Порядок уничтожения')
    security_measures = models.TextField(verbose_name='Применяемые меры защиты')
    created_at = models.DateField(auto_now_add=True, verbose_name='Дата внесения')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Запись реестра обработки ПД'
        verbose_name_plural = 'Реестр обработки ПД'
        ordering = ['created_at']
    
    def __str__(self):
        return self.name

class PrivacyConsent(models.Model):
    """Модель для хранения согласий на обработку персональных данных"""
    
    CONSENT_TYPES = [
        ('registration', 'Согласие при регистрации'),
        ('newsletter', 'Согласие на рассылку'),
        ('marketing', 'Согласие на маркетинговые коммуникации'),
        ('cookies', 'Согласие на использование cookies'),
        ('analytics', 'Согласие на аналитику'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    consent_type = models.CharField(max_length=50, choices=CONSENT_TYPES, verbose_name="Тип согласия")
    version = models.CharField(max_length=20, verbose_name="Версия согласия")
    ip_address = models.GenericIPAddressField(verbose_name="IP-адрес")
    user_agent = models.TextField(verbose_name="User Agent")
    is_active = models.BooleanField(default=True, verbose_name="Действует")
    granted_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата выдачи")
    revoked_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата отзыва")
    
    document_url = models.URLField(blank=True, verbose_name="Ссылка на документ")
    purpose = models.TextField(verbose_name="Цель обработки")
    data_categories = models.JSONField(default=list, verbose_name="Категории данных")
    third_parties = models.JSONField(default=list, verbose_name="Третьи стороны")
    storage_period = models.CharField(max_length=100, verbose_name="Срок хранения")
    
    class Meta:
        verbose_name = "Согласие на обработку ПД"
        verbose_name_plural = "Согласия на обработку ПД"
        unique_together = ['user', 'consent_type', 'version']
        indexes = [
            models.Index(fields=['user', 'consent_type', 'is_active']),
            models.Index(fields=['granted_at', 'is_active']),
        ]
    
    def __str__(self):
        return f"Согласие {self.get_consent_type_display()} - {self.user.username}"
    
    def revoke(self, ip_address=None, user_agent=None):
        """Отзыв согласия"""
        self.is_active = False
        self.revoked_at = timezone.now()
        
        PrivacyConsentLog.objects.create(
            consent=self,
            action='revoked',
            ip_address=ip_address,
            user_agent=user_agent,
            details={'previous_status': 'active'}
        )
        
        if self.consent_type == 'newsletter':
            self.handle_newsletter_unsubscribe()
        
        self.save()
    
    def handle_newsletter_unsubscribe(self):
        """Обработка отписки от рассылки"""
        pass
    
    def is_valid(self):
        """Проверка валидности согласия"""
        return self.is_active
    
    def get_expiration_date(self):
        """Получение даты истечения срока"""
        if self.storage_period == 'until_revoked':
            return None
        
        try:
            if 'year' in self.storage_period:
                years = int(self.storage_period.split()[0])
                return self.granted_at + timedelta(days=365 * years)
        except:
            return None
        
        return None

class PrivacyConsentLog(models.Model):
    """Лог изменений согласий"""
    consent = models.ForeignKey(PrivacyConsent, on_delete=models.CASCADE, verbose_name="Согласие")
    action = models.CharField(max_length=50, verbose_name="Действие")  # created, modified, revoked, etc.
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Пользователь")
    ip_address = models.GenericIPAddressField(verbose_name="IP-адрес")
    user_agent = models.TextField(verbose_name="User Agent")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время")
    details = models.JSONField(default=dict, verbose_name="Детали")
    
    class Meta:
        verbose_name = "Лог согласия"
        verbose_name_plural = "Логи согласий"
        ordering = ['-timestamp']

def create_registration_consent(user, ip_address=None, user_agent=None, request=None):
    """Создание согласия при регистрации"""
    try:
        if not ip_address and request:
            ip_address = get_client_ip(request)
        
        if not user_agent and request:
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        consent = PrivacyConsent.objects.create(
            user=user,
            consent_type='registration',
            version='1.0',
            ip_address=ip_address or '0.0.0.0',
            user_agent=user_agent or 'Unknown',
            purpose='Создание учетной записи, идентификация пользователя, оказание услуг',
            data_categories=['ФИО', 'email', 'телефон', 'адрес', 'пароль (хэшированный)'],
            third_parties=[
                {'name': 'Хостинг-провайдер', 'purpose': 'Хранение данных'},
                {'name': 'Платежный шлюз', 'purpose': 'Обработка платежей'},
                {'name': 'Служба доставки', 'purpose': 'Доставка товаров'},
                {'name': 'Email-сервис', 'purpose': 'Отправка уведомлений'}
            ],
            storage_period='5 years after last activity',
            document_url='/privacy/'  
        )
        
        PrivacyConsentLog.objects.create(
            consent=consent,
            action='created',
            user=user,
            ip_address=ip_address or '0.0.0.0',
            user_agent=user_agent or 'Unknown',
            details={'context': 'registration'}
        )
        
        return consent
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Ошибка создания согласия при регистрации: {str(e)}')
        return None

def get_client_ip(request):
    """Получение реального IP адреса клиента"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

class PriceList(models.Model):
    """Прайс-лист (базовые цены)"""
    name = models.CharField(max_length=200, verbose_name="Название прайс-листа")
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Прайс-лист"
        verbose_name_plural = "Прайс-листы"

class PriceListItem(models.Model):
    """Цена товара в прайс-листе"""
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    currency = models.CharField(max_length=3, default='RUB')
    min_quantity = models.PositiveIntegerField(default=1, verbose_name="Мин. количество")
    
    class Meta:
        unique_together = ['price_list', 'product', 'min_quantity']

class ClientDiscount(models.Model):
    """Персональная скидка для клиента (выдается админом)"""
    DISCOUNT_TYPES = [
        ('percent', 'Процентная'),
        ('fixed', 'Фиксированная'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='discount')
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default='percent')
    discount_value = models.DecimalField(max_digits=5, decimal_places=2, default=0, 
                                         verbose_name="Скидка (%)" if 'percent' else "Скидка (руб)")
    valid_from = models.DateField(auto_now_add=True)
    valid_to = models.DateField(null=True, blank=True, verbose_name="Действует до")
    is_active = models.BooleanField(default=True)
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='issued_discounts')
    issued_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, verbose_name="Причина скидки")
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                              verbose_name="Макс. сумма скидки")
    applicable_categories = models.ManyToManyField('Category', blank=True, verbose_name="Только для категорий")
    
    def apply_to_price(self, original_price):
        """Применить скидку к цене"""
        if not self.is_active:
            return original_price
        
        if self.valid_to and self.valid_to < timezone.now().date():
            return original_price
        
        if self.discount_type == 'percent':
            discounted = original_price * (100 - self.discount_value) / 100
        else:
            discounted = original_price - self.discount_value
        
        if self.max_discount_amount:
            discount_amount = original_price - discounted
            if discount_amount > self.max_discount_amount:
                discounted = original_price - self.max_discount_amount
        
        return max(discounted, 0)
    
    class Meta:
        verbose_name = "Скидка клиента"
        verbose_name_plural = "Скидки клиентов"

class ClientPriceContract(models.Model):
    """Индивидуальный договор цен (для крупных клиентов)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='price_contracts')
    name = models.CharField(max_length=200, verbose_name="Название договора")
    contract_number = models.CharField(max_length=50)
    valid_from = models.DateField()
    valid_to = models.DateField()
    contract_file = models.FileField(upload_to='contracts/%Y/%m/', blank=True)
    special_prices = models.JSONField(default=dict, blank=True, 
                                      verbose_name="Спеццены {product_id: price}")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Contract(models.Model):
    """Договор с клиентом"""
    CONTRACT_TYPES = [
        ('supply', 'Договор поставки'),
        ('service', 'Договор оказания услуг'),
        ('nda', 'Соглашение о конфиденциальности'),
        ('framework', 'Рамочный договор'),
    ]
    
    number = models.CharField(max_length=50, unique=True)
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contracts')
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPES)
    
    signed_at = models.DateField()
    valid_from = models.DateField()
    valid_to = models.DateField()
    
    signed_file = models.FileField(upload_to='contracts/signed/%Y/%m/', verbose_name="Подписанный договор")
    scan_file = models.FileField(upload_to='contracts/scans/%Y/%m/', blank=True)
    
    auto_renew = models.BooleanField(default=False)
    renewal_notice_days = models.IntegerField(default=30, verbose_name="Дней до уведомления")
    
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Черновик'),
        ('sent', 'Отправлен'),
        ('signed', 'Подписан'),
        ('expired', 'Истек'),
        ('terminated', 'Расторгнут'),
    ], default='draft')
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_contracts')
    created_at = models.DateTimeField(auto_now_add=True)

class CommercialOffer(models.Model):
    """Коммерческое предложение"""
    number = models.CharField(max_length=50, unique=True)
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offers')
    
    valid_until = models.DateField(verbose_name="Действительно до")
    
    items = models.JSONField(default=list, verbose_name="Позиции")
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    delivery_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Черновик'),
        ('sent', 'Отправлен'),
        ('approved', 'Согласован'),
        ('rejected', 'Отклонен'),
        ('converted', 'Преобразован в заказ'),
        ('expired', 'Истек'),
    ], default='draft')
    
    converted_to_order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True)
    
    pdf_file = models.FileField(upload_to='offers/%Y/%m/', blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_offers')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Коммерческое предложение"
        verbose_name_plural = "Коммерческие предложения"