from django.core.management.base import BaseCommand
from main.models import Order

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Исправляем исторические оплаченные заказы
        paid_orders = Order.objects.filter(status='paid')
        fixed_count = 0
        
        for order in paid_orders:
            if not order.is_payment_finalized:
                order.finalize_payment()
                fixed_count += 1
                self.stdout.write(f"Fixed order #{order.id}")
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Fixed {fixed_count} orders')
        )