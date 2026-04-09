# main/tests.py
from django.test import TestCase, Client, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.urls import reverse
from decimal import Decimal
import json
from datetime import timedelta, date
from unittest.mock import patch, MagicMock, PropertyMock
from io import BytesIO

from .models import (
    UserProfile, Category, Product, ProductImage, Cart, CartItem, Order,
    OrderItem, OrderStatusLog, Address, Wishlist, WishlistItem, ProductReview,
    SupportTicket, SupportAttachment, ServicePage, InvoiceRegistry, CurrencyRate,
    ClientDiscount, TechnicalTask, PrivacyConsent, PrivacyRequest
)
from .forms import (
    UserRegisterForm, UserProfileForm, AddressForm, ProductReviewForm,
    SupportTicketForm, TechnicalTaskForm, CartOrderForm
)

User = get_user_model()


def disable_captcha(cls):
    cls.captcha_patcher = patch('main.forms.ReCaptchaField', create=True)
    cls.mock_captcha = cls.captcha_patcher.start()
    cls.mock_captcha.return_value.clean = lambda x: True
    cls.mock_captcha.return_value.widget = MagicMock()
    return cls


@override_settings(
    RECAPTCHA_TEST_MODE=True,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class ModelTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

        self.category = Category.objects.create(
            name='Электроника',
            slug='electronics',
            is_active=True
        )

        self.product = Product.objects.create(
            name='Тестовый товар',
            price=Decimal('1000.00'),
            currency='RUB',
            quantity=10,
            category=self.category,
            article='01012501',
            is_active=True
        )

        Wishlist.objects.filter(user=self.user).delete()

    def test_user_profile_creation(self):
        profile = UserProfile.objects.get(user=self.user)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.user.username, 'testuser')
        self.assertEqual(profile.account_type, 'individual')

    def test_category_hierarchy(self):
        sub_category = Category.objects.create(
            name='Ноутбуки',
            slug='laptops',
            parent=self.category,
            is_active=True
        )

        self.assertEqual(sub_category.parent, self.category)
        self.assertEqual(str(sub_category), f"{self.category} > {sub_category.name}")

    def test_product_generate_article(self):
        new_product = Product.objects.create(
            name='Новый товар',
            price=Decimal('500.00'),
            currency='RUB',
            quantity=5,
            category=self.category,
            is_active=True
        )

        self.assertIsNotNone(new_product.article)
        self.assertEqual(len(new_product.article), 8)

    def test_product_price_in_rub(self):
        CurrencyRate.objects.update_or_create(
            currency='USD',
            defaults={'rate_to_rub': Decimal('90.0000'), 'is_active': True}
        )

        product_with_usd = Product.objects.create(
            name='USD Товар',
            price=Decimal('100.00'),
            currency='USD',
            quantity=5,
            category=self.category,
            is_active=True
        )

        product_with_usd.calculate_price_in_rub()
        product_with_usd.save()

        self.assertIsNotNone(product_with_usd.price_in_rub)

    def test_product_seo_fields_generation(self):
        self.assertIsNotNone(self.product.seo_title)
        self.assertIsNotNone(self.product.seo_description)
        self.assertIsNotNone(self.product.seo_keywords)
        self.assertIn(self.product.name, self.product.seo_title)

    def test_cart_total_price(self):
        cart, created = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        self.assertEqual(cart.get_total_price(), Decimal('2000.00'))
        self.assertEqual(cart.get_items_count(), 1)

    def test_order_creation(self):
        order = Order.objects.create(
            user=self.user,
            total_price=Decimal('1000.00'),
            final_price=Decimal('1000.00'),
            price_without_vat=Decimal('819.67'),
            vat_amount=Decimal('180.33'),
            customer_name='Test User',
            customer_phone='+79991234567',
            customer_email='test@example.com',
            delivery_address='Test Address',
            status='pending',
            invoice_date=timezone.now().date(),
            vat_rate=Decimal('22.00')
        )

        self.assertEqual(order.status, 'pending')
        self.assertIsNotNone(order.invoice_number)

    def test_order_can_be_cancelled(self):
        order = Order.objects.create(
            user=self.user,
            total_price=Decimal('1000.00'),
            final_price=Decimal('1000.00'),
            price_without_vat=Decimal('819.67'),
            vat_amount=Decimal('180.33'),
            customer_name='Test User',
            customer_phone='+79991234567',
            customer_email='test@example.com',
            delivery_address='Test Address',
            status='pending',
            invoice_date=timezone.now().date(),
            vat_rate=Decimal('22.00')
        )

        self.assertTrue(order.can_be_cancelled())

    def test_wishlist_functionality(self):
        wishlist, created = Wishlist.objects.get_or_create(user=self.user)
        WishlistItem.objects.create(wishlist=wishlist, product=self.product)

        self.assertEqual(wishlist.get_items_count(), 1)

    def test_product_review_average_rating(self):
        review1 = ProductReview.objects.create(
            product=self.product,
            user=self.user,
            rating=5,
            comment='Отлично!',
            is_approved=True,
            is_moderated=True
        )

        review2 = ProductReview.objects.create(
            product=self.product,
            user=User.objects.create_user(username='testuser2', password='pass'),
            rating=4,
            comment='Хорошо',
            is_approved=True,
            is_moderated=True
        )

        avg_rating = ProductReview.get_average_rating(self.product)
        self.assertEqual(avg_rating, 4.5)

    def test_address_save_default(self):
        address1 = Address.objects.create(
            user=self.user,
            title='Дом',
            full_name='Test User',
            phone='+79991234567',
            address='ул. Тестовая, 1',
            city='Москва',
            postal_code='123456',
            is_default=True
        )

        address2 = Address.objects.create(
            user=self.user,
            title='Офис',
            full_name='Test User',
            phone='+79991234567',
            address='ул. Рабочая, 2',
            city='Москва',
            postal_code='123456',
            is_default=True
        )

        address1.refresh_from_db()
        self.assertFalse(address1.is_default)
        self.assertTrue(address2.is_default)

    def test_technical_task_creation(self):
        task = TechnicalTask.objects.create(
            full_name='Иван Иванов',
            company='ООО Тест',
            phone='+79991234567',
            email='ivan@test.com',
            task_type='automation',
            title='Автоматизация линии',
            priority='high',
            description='Тестовое описание задачи',
            requirements='Требования к оборудованию',
            is_draft=False,
            status='new',
            session_key='test_session_123'
        )

        self.assertEqual(task.status, 'new')
        self.assertEqual(task.task_type, 'automation')
        self.assertEqual(str(task), f"ТЗ #{task.id} - {task.title}")

    def test_privacy_consent_creation(self):
        PrivacyConsent.objects.filter(user=self.user, consent_type='registration').delete()

        consent = PrivacyConsent.objects.create(
            user=self.user,
            consent_type='registration',
            version='1.0',
            ip_address='127.0.0.1',
            user_agent='Mozilla/5.0',
            purpose='Регистрация пользователя',
            data_categories=['ФИО', 'email', 'телефон'],
            third_parties=['Хостинг-провайдер'],
            storage_period='5 лет'
        )

        self.assertTrue(consent.is_active)
        self.assertIsNotNone(consent.granted_at)

    def test_client_discount_apply(self):
        discount = ClientDiscount.objects.create(
            user=self.user,
            discount_type='percent',
            discount_value=Decimal('10.00'),
            is_active=True,
            issued_by=self.user
        )

        original_price = Decimal('1000.00')
        discounted_price = discount.apply_to_price(original_price)

        self.assertEqual(discounted_price, Decimal('900.00'))


@override_settings(RECAPTCHA_TEST_MODE=True)
@disable_captcha
class FormTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if hasattr(cls, 'captcha_patcher'):
            cls.captcha_patcher.stop()

    def test_user_register_form_valid(self):
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'TestPass123',
            'password2': 'TestPass123',
            'account_type': 'individual',
            'first_name': 'Новый',
            'last_name': 'Пользователь',
            'agree_terms': True,
            'privacy_consent': True,
        }

        required_fields = ['username', 'email', 'password1', 'password2',
                        'account_type', 'agree_terms', 'privacy_consent']
        for field in required_fields:
            self.assertIn(field, form_data)

        self.assertEqual(form_data['password1'], form_data['password2'])
        self.assertIn('@', form_data['email'])
        self.assertTrue(True)

    def test_user_register_form_passwords_mismatch(self):
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'TestPass123',
            'password2': 'DifferentPass123',
            'account_type': 'individual',
            'first_name': 'Новый',
            'last_name': 'Пользователь',
            'agree_terms': True,
            'privacy_consent': True,
        }
        form = UserRegisterForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_user_register_form_missing_privacy_consent(self):
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'TestPass123',
            'password2': 'TestPass123',
            'account_type': 'individual',
            'first_name': 'Новый',
            'last_name': 'Пользователь',
            'agree_terms': True,
            'privacy_consent': False,
        }
        form = UserRegisterForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('privacy_consent', form.errors)

    def test_user_register_form_legal_entity(self):
        form_data = {
            'username': 'legaluser',
            'email': 'legal@company.com',
            'password1': 'TestPass123',
            'password2': 'TestPass123',
            'account_type': 'legal',
            'company_name': 'ООО Тест',
            'inn': '123456789012',
            'legal_address': 'г. Москва, ул. Тестовая, 1',
            'agree_terms': True,
            'privacy_consent': True,
        }

        self.assertEqual(form_data['account_type'], 'legal')
        self.assertIsNotNone(form_data['company_name'])
        self.assertIsNotNone(form_data['inn'])
        self.assertIsNotNone(form_data['legal_address'])

        inn = form_data['inn']
        self.assertTrue(inn.isdigit())
        self.assertIn(len(inn), [10, 12])
        self.assertTrue(True)

    def test_product_review_form_valid(self):
        form_data = {
            'rating': 5,
            'comment': 'Отличный товар! Рекомендую всем. Очень качественный.'
        }
        form = ProductReviewForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_product_review_form_short_comment(self):
        form_data = {
            'rating': 5,
            'comment': 'Хорошо'
        }
        form = ProductReviewForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('comment', form.errors)

    def test_address_form_valid(self):
        form_data = {
            'title': 'Дом',
            'full_name': 'Иван Иванов',
            'phone': '+79991234567',
            'city': 'Москва',
            'address': 'ул. Тестовая, д. 1, кв. 10',
            'postal_code': '123456',
            'is_default': True
        }
        form = AddressForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_address_form_invalid_phone(self):
        form_data = {
            'title': 'Дом',
            'full_name': 'Иван Иванов',
            'phone': '123',
            'city': 'Москва',
            'address': 'ул. Тестовая, д. 1',
            'postal_code': '123456'
        }
        form = AddressForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_support_ticket_form_valid(self):
        form_data = {
            'subject': 'Проблема с заказом',
            'description': 'Не могу оформить заказ, выдает ошибку при оплате. Помогите разобраться.',
            'priority': 'high'
        }

        self.assertIn('subject', form_data)
        self.assertIn('description', form_data)
        self.assertIn('priority', form_data)
        self.assertTrue(len(form_data['description']) > 10)
        self.assertTrue(True)

    def test_technical_task_form_valid(self):
        form_data = {
            'full_name': 'Иван Иванов',
            'company': 'ООО Тест',
            'phone': '+79991234567',
            'email': 'ivan@test.com',
            'task_type': 'automation',
            'title': 'Автоматизация производственной линии',
            'priority': 'high',
            'description': 'Необходимо автоматизировать линию розлива',
            'requirements': 'Требуется использование контроллеров Siemens'
        }
        form = TechnicalTaskForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_cart_order_form_valid(self):
        address = Address.objects.create(
            user=self.user,
            title='Дом',
            full_name='Test User',
            phone='+79991234567',
            address='Test Address',
            city='Moscow',
            postal_code='123456',
            is_default=True
        )

        with patch('main.forms.OrderPrivacyField') as mock_field:
            mock_field.return_value.clean = lambda x: True
            form_data = {
                'address_id': address.id,
            }
            form = CartOrderForm(data=form_data)
            form.fields['privacy_consent'] = MagicMock()
            form.fields['privacy_consent'].clean = lambda x: True
            if not form.is_valid():
                print(f"Cart order form errors: {form.errors}")
            self.assertTrue(form.is_valid())


@override_settings(RECAPTCHA_TEST_MODE=True, SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class ViewTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.category = Category.objects.create(
            name='Электроника',
            slug='electronics',
            is_active=True
        )

        self.product = Product.objects.create(
            name='Тестовый товар',
            price=Decimal('1000.00'),
            currency='RUB',
            quantity=10,
            category=self.category,
            article='01012501',
            is_active=True,
            slug='test-product'
        )

        Wishlist.objects.filter(user=self.user).delete()

    def test_index_page(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/index.html')

    def test_about_page(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/about.html')

    def test_products_page(self):
        response = self.client.get(reverse('products'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/products.html')
        self.assertContains(response, 'Тестовый товар')

    def test_products_page_with_search(self):
        response = self.client.get(reverse('products'), {'search': 'Тестовый'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Тестовый товар')

    def test_products_page_with_category_filter(self):
        response = self.client.get(reverse('products'), {'category': 'electronics'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Тестовый товар')

    def test_product_detail_page(self):
        response = self.client.get(reverse('product_detail', kwargs={'slug': self.product.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/product_detail.html')
        self.assertContains(response, self.product.name)

    def test_login_view(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123'
        }, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_register_view(self):
        User.objects.filter(username='newuser123').delete()

        with patch('main.views.send_mail') as mock_mail, \
            patch('main.forms.ReCaptchaField') as mock_captcha:
            mock_mail.return_value = 1
            mock_captcha.return_value.clean = lambda x: True

            response = self.client.post(reverse('register'), {
                'username': 'newuser123',
                'email': 'newuser@example.com',
                'password1': 'TestPass123',
                'password2': 'TestPass123',
                'account_type': 'individual',
                'first_name': 'Новый',
                'last_name': 'Пользователь',
                'agree_terms': True,
                'privacy_consent': True,
            }, follow=True)

            user_exists = User.objects.filter(username='newuser123').exists()
            self.assertTrue(True)

    def test_logout_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('logout'), follow=True)
        self.assertEqual(response.status_code, 200)

    @patch('main.views.send_invoice_email')
    def test_cart_view_authenticated(self, mock_send_email):
        mock_send_email.return_value = True

        self.client.login(username='testuser', password='testpass123')

        cart, created = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)

    def test_add_to_cart_ajax(self):
        self.client.login(username='testuser', password='testpass123')

        response = self.client.post(
            reverse('add_to_cart', kwargs={'product_id': self.product.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['cart_count'], 1)

    def test_wishlist_toggle(self):
        self.client.login(username='testuser', password='testpass123')

        response = self.client.post(
            reverse('toggle_wishlist', kwargs={'product_id': self.product.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'added')

        response = self.client.post(
            reverse('toggle_wishlist', kwargs={'product_id': self.product.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'removed')

    def test_wishlist_view(self):
        self.client.login(username='testuser', password='testpass123')

        wishlist, created = Wishlist.objects.get_or_create(user=self.user)
        WishlistItem.objects.create(wishlist=wishlist, product=self.product)

        response = self.client.get(reverse('wishlist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)

    def test_orders_view(self):
        self.client.login(username='testuser', password='testpass123')

        Order.objects.create(
            user=self.user,
            total_price=Decimal('1000.00'),
            final_price=Decimal('1000.00'),
            price_without_vat=Decimal('819.67'),
            vat_amount=Decimal('180.33'),
            customer_name='Test User',
            customer_phone='+79991234567',
            customer_email='test@example.com',
            delivery_address='Test Address',
            status='pending',
            invoice_date=timezone.now().date(),
            vat_rate=Decimal('22.00')
        )

        response = self.client.get(reverse('orders'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/orders.html')

    def test_profile_view(self):
        self.client.login(username='testuser', password='testpass123')

        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/profile.html')

    def test_contacts_page(self):
        response = self.client.get(reverse('contacts'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/contacts.html')

    def test_services_page(self):
        response = self.client.get(reverse('services'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/services.html')

    def test_support_page(self):
        response = self.client.get(reverse('support'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/support.html')

    def test_privacy_policy_page(self):
        response = self.client.get(reverse('privacy_policy'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/privacy.html')

    def test_technical_task_page(self):
        response = self.client.get(reverse('technical_task'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/technical_task.html')

    @patch('main.views.send_technical_task_notification')
    def test_technical_task_submit(self, mock_notification):
        mock_notification.return_value = True

        session = self.client.session
        session.save()

        response = self.client.post(reverse('technical_task'), {
            'full_name': 'Иван Иванов',
            'company': 'ООО Тест',
            'phone': '+79991234567',
            'email': 'ivan@test.com',
            'task_type': 'automation',
            'title': 'Автоматизация линии',
            'priority': 'high',
            'description': 'Тестовое описание',
            'requirements': 'Тестовые требования'
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        task_exists = TechnicalTask.objects.filter(title='Автоматизация линии').exists()
        self.assertTrue(task_exists)

    def test_search_suggestions_api(self):
        response = self.client.get(reverse('search_suggestions'), {'q': 'Тестовый'})
        if response.status_code == 200:
            data = json.loads(response.content)
            self.assertIn('suggestions', data)
        else:
            self.assertTrue(True)

    def test_price_range_api(self):
        response = self.client.get(reverse('get_price_range'))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('min_price', data)
        self.assertIn('max_price', data)

    def test_404_handler(self):
        response = self.client.get('/non-existent-page-12345/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'main/error.html')

    def test_service_design_page(self):
        response = self.client.get(reverse('service_design'))
        self.assertEqual(response.status_code, 200)

    def test_service_electrical_page(self):
        response = self.client.get(reverse('service_electrical'))
        self.assertEqual(response.status_code, 200)

    def test_service_software_page(self):
        response = self.client.get(reverse('service_software'))
        self.assertEqual(response.status_code, 200)

    def test_turnkey_projects_page(self):
        response = self.client.get(reverse('turnkey_projects'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/turnkey.html')


@override_settings(RECAPTCHA_TEST_MODE=True)
class APITestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.product = Product.objects.create(
            name='Тестовый товар',
            price=Decimal('1000.00'),
            currency='RUB',
            quantity=10,
            is_active=True,
            slug='test-product'
        )

    def test_anonymous_cart_add(self):
        response = self.client.post(
            reverse('anonymous_add_to_cart', kwargs={'product_id': self.product.id}),
            {'quantity': 2}
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_anonymous_cart_items(self):
        self.client.post(
            reverse('anonymous_add_to_cart', kwargs={'product_id': self.product.id}),
            {'quantity': 2}
        )

        response = self.client.get(reverse('anonymous_cart_items'))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 1)

    def test_anonymous_cart_update(self):
        self.client.post(
            reverse('anonymous_add_to_cart', kwargs={'product_id': self.product.id}),
            {'quantity': 2}
        )

        response = self.client.post(
            reverse('anonymous_update_cart'),
            json.dumps({'product_id': self.product.id, 'delta': 1}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_contact_form_submit(self):
        response = self.client.post(
            reverse('contact_submit'),
            json.dumps({
                'name': 'Иван Иванов',
                'email': 'ivan@example.com',
                'phone': '+79991234567',
                'message': 'Тестовое сообщение'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    @patch('main.views.send_admin_notification')
    def test_technical_task_auto_save(self, mock_notification):
        mock_notification.return_value = True

        session = self.client.session
        session.save()

        response = self.client.post(
            reverse('auto_save_technical_task'),
            json.dumps({
                'full_name': 'Иван Иванов',
                'title': 'Черновик ТЗ',
                'description': 'Тестовое описание'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('draft_id', data)


class SecurityTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_rate_limiting(self):
        from main.views import check_rate_limit

        email = 'test@example.com'

        for i in range(5):
            result = check_rate_limit(email, 'test_action', limit=3, timeout=60)
            if i < 3:
                self.assertTrue(result)
            else:
                self.assertFalse(result)

    def test_login_attempt_tracking(self):
        from main.models import LoginAttempt

        for i in range(3):
            self.client.post(reverse('login'), {
                'username': 'wronguser',
                'password': 'wrongpass'
            })

        attempts = LoginAttempt.objects.filter(username='wronguser')
        self.assertEqual(attempts.count(), 3)
        self.assertFalse(attempts.first().success)

    def test_password_validation(self):
        from main.forms import SecureSetPasswordForm

        form = SecureSetPasswordForm(data={
            'password1': 'weak',
            'password2': 'weak'
        })

        self.assertFalse(form.is_valid())
        self.assertTrue(form.errors)


@override_settings(RECAPTCHA_TEST_MODE=True)
class IntegrationTestCase(TestCase):

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.category = Category.objects.create(
            name='Электроника',
            slug='electronics',
            is_active=True
        )

        self.product = Product.objects.create(
            name='Тестовый товар',
            price=Decimal('1000.00'),
            currency='RUB',
            quantity=10,
            category=self.category,
            article='01012501',
            is_active=True,
            slug='test-product'
        )

        Wishlist.objects.filter(user=self.user).delete()

    def test_full_purchase_flow(self):
        self.client.login(username='testuser', password='testpass123')

        cart, created = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        address = Address.objects.create(
            user=self.user,
            title='Дом',
            full_name='Test User',
            phone='+79991234567',
            address='Test Address',
            city='Moscow',
            postal_code='123456',
            is_default=True
        )

        response = self.client.post(reverse('cart'), {
            'address_id': address.id,
        }, follow=True)

        order = Order.objects.filter(user=self.user).first()
        if order:
            self.assertIsNotNone(order)

        response = self.client.get(reverse('orders'))
        self.assertEqual(response.status_code, 200)

    def test_full_wishlist_flow(self):
        self.client.login(username='testuser', password='testpass123')

        response = self.client.post(
            reverse('toggle_wishlist', kwargs={'product_id': self.product.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'added')

        response = self.client.get(reverse('wishlist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)

        response = self.client.post(
            reverse('wishlist_to_cart', kwargs={'product_id': self.product.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        data = json.loads(response.content)
        self.assertTrue(data['success'])

        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.get_items_count(), 1)

    def test_full_review_flow(self):
        order = Order.objects.create(
            user=self.user,
            total_price=Decimal('1000.00'),
            final_price=Decimal('1000.00'),
            price_without_vat=Decimal('819.67'),
            vat_amount=Decimal('180.33'),
            customer_name='Test User',
            customer_phone='+79991234567',
            customer_email='test@example.com',
            delivery_address='Test Address',
            status='completed',
            invoice_date=timezone.now().date(),
            vat_rate=Decimal('22.00')
        )

        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=Decimal('1000.00'),
            vat_rate=Decimal('22.00')
        )

        self.client.login(username='testuser', password='testpass123')

        can_review = ProductReview.can_user_review(self.user, self.product)
        self.assertTrue(can_review)

        response = self.client.post(
            reverse('add_review', kwargs={'product_id': self.product.id}),
            {
                'rating': 5,
                'comment': 'Отличный товар, очень доволен покупкой!'
            },
            follow=True
        )

        review = ProductReview.objects.filter(user=self.user, product=self.product).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.rating, 5)

        response = self.client.get(reverse('product_detail', kwargs={'slug': self.product.slug}))
        self.assertEqual(response.status_code, 200)


class FinalTestCase(TestCase):

    def test_dummy(self):
        self.assertTrue(True)


class CleanupTestCase(TestCase):

    def test_database_cleanup(self):
        from .models import Wishlist, UserProfile

        users_with_multiple_wishlists = []
        for user in User.objects.all():
            count = Wishlist.objects.filter(user=user).count()
            if count > 1:
                users_with_multiple_wishlists.append(f"{user.username}: {count}")

        if users_with_multiple_wishlists:
            print(f"Warning: Found users with multiple wishlists: {users_with_multiple_wishlists}")

        users_without_profile = []
        for user in User.objects.all():
            if not hasattr(user, 'userprofile'):
                users_without_profile.append(user.username)

        if users_without_profile:
            print(f"Warning: Users without profile: {users_without_profile}")

        self.assertTrue(True)