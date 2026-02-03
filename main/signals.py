# main/signals.py 

from django.db.models.signals import post_save, pre_delete, post_delete, pre_save
from django.dispatch import receiver
from .models import UserProfile, User, Wishlist, Admin2FA, ProductReview
from django.core.cache import cache
import os
from main.models import PrivacyConsent

@receiver(post_save, sender=ProductReview)
def auto_moderate_review(sender, instance, created, **kwargs):
    """Автоматическая модерация отзывов"""
    if created and not instance.is_moderated:
        if instance.rating >= 4:
            instance.is_moderated = True
            instance.is_approved = True
            instance.save()

@receiver(pre_delete, sender=UserProfile)
def delete_profile_images(sender, instance, **kwargs):
    """Безопасное удаление изображений профиля при удалении"""
    import os
    
    def safe_delete(file_field):
        """Безопасное удаление файла"""
        try:
            if file_field and hasattr(file_field, 'path'):
                file_path = file_field.path
                if os.path.isfile(file_path):
                    os.remove(file_path)
        except (OSError, ValueError, TypeError):
            pass
    
    # Удаляем все изображения профиля
    safe_delete(instance.avatar)
    safe_delete(instance.avatar_small)
    safe_delete(instance.avatar_medium)
    safe_delete(instance.avatar_large)
    safe_delete(instance.profile_background)

@receiver(pre_save, sender=UserProfile)
def delete_old_images(sender, instance, **kwargs):
    """Удаление старых изображений при загрузке новых"""
    if not instance.pk:
        return False
    
    try:
        old_instance = UserProfile.objects.get(pk=instance.pk)
    except UserProfile.DoesNotExist:
        return False
    
    import os
    
    def safe_delete(old_file, new_file, field_name):
        """Безопасное удаление старого файла если загружен новый"""
        try:
            if old_file and hasattr(old_file, 'path'):
                old_path = old_file.path
                new_path = new_file.path if new_file else None
                
                # Удаляем если:
                # 1. Есть старый файл
                # 2. Нет нового ИЛИ новый файл отличается от старого
                # 3. Файл существует
                if (old_path and os.path.isfile(old_path) and 
                    (not new_file or old_path != new_path)):
                    os.remove(old_path)
        except (OSError, ValueError, TypeError):
            pass
    
    # Проверяем каждое поле с изображением
    safe_delete(old_instance.avatar, instance.avatar, 'avatar')
    safe_delete(old_instance.avatar_small, instance.avatar_small, 'avatar_small')
    safe_delete(old_instance.avatar_medium, instance.avatar_medium, 'avatar_medium')
    safe_delete(old_instance.avatar_large, instance.avatar_large, 'avatar_large')
    safe_delete(old_instance.profile_background, instance.profile_background, 'profile_background')

@receiver(post_save, sender=UserProfile)
def clear_profile_cache(sender, instance, **kwargs):
    """Очистка кэша при обновлении профиля"""
    cache_keys = [
        f'profile_{instance.user_id}',
        f'profile_card_{instance.user_id}',
        f'profile_{instance.profile_slug}',
    ]
    for key in cache_keys:
        cache.delete(key)

@receiver(post_save, sender=User)
def create_default_privacy_consent(sender, instance, created, **kwargs):
    """Автоматически создаем согласие при создании пользователя"""
    if created:
        if not PrivacyConsent.objects.filter(user=instance, consent_type='registration').exists():
            PrivacyConsent.objects.create(
                user=instance,
                consent_type='registration',
                version='1.0',
                ip_address='127.0.0.1', 
                user_agent='System',
                purpose='Обработка персональных данных для регистрации',
                data_categories=['email', 'username', 'password_hash'],
                third_parties=[],
                storage_period='до отзыва пользователем'
            )