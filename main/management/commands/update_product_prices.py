# main/management/commands/update_product_prices.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import Product
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Обновляет цены в рублях для всех товаров в иностранной валюте'
    
    def handle(self, *args, **options):
        try:
            self.stdout.write(f"[{timezone.now()}] Начало пересчета цен товаров")
            
            products = Product.objects.exclude(currency='RUB')
            updated_count = 0
            
            for product in products:
                try:
                    if product.update_price_from_currency():
                        updated_count += 1
                except Exception as e:
                    logger.error(f"Ошибка обновления цены для товара {product.article}: {str(e)}")
                    continue
            
            self.stdout.write(
                self.style.SUCCESS(f"[{timezone.now()}] Обновлено {updated_count} из {products.count()} товаров")
            )
            
        except Exception as e:
            logger.error(f"Ошибка в update_product_prices: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f"Ошибка: {str(e)}")
            )