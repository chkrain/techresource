# main/services/cardlink_service.py
import requests
import hashlib
import hmac
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

class CardlinkService:
    def __init__(self):
        self.merchant_id = settings.CARDLINK_MERCHANT_ID
        self.secret_key = settings.CARDLINK_SECRET_KEY
        self.api_url = settings.CARDLINK_API_URL
        self.token = settings.CARDLINK_TOKEN
        self.is_test_mode = self._check_test_mode()
        
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def _check_test_mode(self):
        """Проверяем, используем ли мы тестовые данные"""
        return any([
            'test' in (self.merchant_id or '').lower(),
            'test' in (self.secret_key or '').lower(), 
            'test' in (self.token or '').lower(),
            'sandbox' in (self.api_url or '').lower(),
            settings.DEBUG  # В режиме DEBUG используем mock
        ])

    def create_bill(self, order, request):
        """Создание счета в Cardlink"""
        # Проверяем наличие обязательных настроек
        if not all([self.merchant_id, self.secret_key, self.token]):
            print("❌ Настройки Cardlink не заданы, используем mock режим")
            return self._create_mock_bill(order, request)
        # Если тестовый режим - возвращаем mock данные
        if self.is_test_mode:
            print("🧪 Тестовый режим Cardlink, используем mock")
            return self._create_mock_bill(order, request)
        
        try:
            # Формируем данные для счета
            bill_data = {
                'amount': float(order.total_price),
                'currency': 'RUB',
                'order_id': str(order.id),
                'description': f'Заказ #{order.id}',
                'success_url': self._build_absolute_url(request, 'cardlink_payment_success', args=[order.id]),
                'fail_url': self._build_absolute_url(request, 'payment_failed', args=[order.id]),
                'callback_url': self._build_absolute_url(request, 'cardlink_webhook'),
                'refund_url': self._build_absolute_url(request, 'cardlink_webhook_refund'),
                'chargeback_url': self._build_absolute_url(request, 'cardlink_webhook_chargeback'),
                'custom': f'user_{order.user.id}',
                'client_email': order.customer_email,
                'client_name': order.customer_name,
            }

            # Создаем подпись
            bill_data['signature'] = self._generate_signature(bill_data)

            print(f"🔗 Отправка запроса к Cardlink API: {self.api_url}/bill/create")
            print(f"📦 Данные счета: {bill_data}")

            # Отправляем запрос к API Cardlink
            response = requests.post(
                f'{self.api_url}/bill/create',
                json=bill_data,
                headers=self.headers,
                timeout=30
            )

            print(f"📡 Ответ Cardlink: {response.status_code} - {response.text}")

            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'payment_url': data.get('payment_url'),
                    'bill_id': data.get('id'),
                    'data': data
                }
            else:
                return {
                    'success': False,
                    'error': f'Cardlink API error: {response.status_code} - {response.text}'
                }

        except Exception as e:
            print(f"❌ Ошибка Cardlink service: {str(e)}")
            return {
                'success': False,
                'error': f'Cardlink service error: {str(e)}'
            }

    def get_bill_status(self, bill_id):
        """Получение статуса счета"""
        try:
            response = requests.get(
                f'{self.api_url}/bill/{bill_id}',
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                return None

        except Exception as e:
            print(f"Error getting bill status: {e}")
            return None

    def _generate_signature(self, data):
        """Генерация подписи для запроса"""
        # Формируем строку для подписи согласно документации Cardlink
        sign_string = f"{data['amount']}:{data['order_id']}:{self.secret_key}"
        return hashlib.md5(sign_string.encode()).hexdigest().upper()

    def _build_absolute_url(self, request, view_name, args=None):
        """Построение абсолютного URL"""
        relative_url = reverse(view_name, args=args) if args else reverse(view_name)
        return request.build_absolute_uri(relative_url)

    def verify_callback_signature(self, data):
        """Проверка подписи callback уведомления"""
        try:
            received_signature = data.get('SignatureValue', '')
            out_sum = data.get('OutSum', '')
            inv_id = data.get('InvId', '')
            
            # Генерируем подпись для проверки
            sign_string = f"{out_sum}:{inv_id}:{self.secret_key}"
            calculated_signature = hashlib.md5(sign_string.encode()).hexdigest().upper()
            
            return received_signature == calculated_signature
        except Exception as e:
            print(f"Error verifying signature: {e}")
            return False
        
    def _create_mock_bill(self, order, request):
        """Создание mock счета для тестирования"""
        mock_payment_url = self._build_absolute_url(request, 'cardlink_mock_process', args=[order.id])
        
        print(f"🧪 Mock режим: создан счет для заказа #{order.id}")
        print(f"🔗 Mock URL: {mock_payment_url}")
        
        return {
            'success': True,
            'payment_url': mock_payment_url,
            'bill_id': f"mock_bill_{order.id}_{timezone.now().timestamp()}",
            'data': {
                'id': f"mock_bill_{order.id}",
                'payment_url': mock_payment_url,
                'status': 'created'
            }
        }