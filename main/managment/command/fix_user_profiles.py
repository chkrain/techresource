# main/management/commands/fix_user_profiles.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from main.models import UserProfile

class Command(BaseCommand):
    help = 'Создает профили для пользователей у которых их нет'

    def handle(self, *args, **options):
        users_without_profiles = User.objects.filter(userprofile__isnull=True)
        
        for user in users_without_profiles:
            UserProfile.objects.create(user=user)
            self.stdout.write(
                self.style.SUCCESS(f'Создан профиль для пользователя {user.username}')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Создано профилей: {users_without_profiles.count()}')
        )