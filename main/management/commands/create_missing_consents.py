# management/commands/create_missing_consents.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from main.models import PrivacyConsent
import json

class Command(BaseCommand):
    help = 'Создает согласия для пользователей у которых их нет'
    
    def handle(self, *args, **kwargs):
        users_without_consent = []
        
        for user in User.objects.all():
            if not PrivacyConsent.objects.filter(user=user).exists():
                users_without_consent.append(user)
                
                PrivacyConsent.objects.create(
                    user=user,
                    consent_type='registration',
                    version='1.0',
                    ip_address='127.0.0.1',  
                    user_agent='System Migration',
                    purpose='Обработка персональных данных для регистрации',
                    data_categories=['email', 'username', 'password_hash'],
                    third_parties=[],
                    storage_period='до отзыва пользователем'
                )
                
                self.stdout.write(f"✓ Создано согласие для {user.username}")
        
        if users_without_consent:
            self.stdout.write(self.style.SUCCESS(
                f'Создано согласий: {len(users_without_consent)}'
            ))
        else:
            self.stdout.write(self.style.WARNING('Все пользователи уже имеют согласия'))