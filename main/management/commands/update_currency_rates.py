# main/management/commands/update_currency_rates.py
from django.core.management.base import BaseCommand
from django.utils import timezone
import logging
from main.models import CurrencyRate

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Обновляет курсы валют с сайта ЦБ РФ'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительное обновление даже если недавно обновлялось'
        )
    
    def handle(self, *args, **options):
        try:
            self.stdout.write(f"[{timezone.now()}] Начало обновления курсов валют")
            
            success = CurrencyRate.update_rates_from_cbr()
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f"[{timezone.now()}] Курсы валют успешно обновлены")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"[{timezone.now()}] Ошибка обновления курсов валют")
                )
                
        except Exception as e:
            logger.error(f"Ошибка обновления курсов: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f"Ошибка: {str(e)}")
            )