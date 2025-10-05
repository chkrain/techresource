# main/signals.py 

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ProductReview

@receiver(post_save, sender=ProductReview)
def auto_moderate_review(sender, instance, created, **kwargs):
    """Автоматическая модерация отзывов"""
    if created and not instance.is_moderated:
        # Автоматически одобряем отзывы с высоким рейтингом
        if instance.rating >= 4:
            instance.is_moderated = True
            instance.is_approved = True
            instance.save()