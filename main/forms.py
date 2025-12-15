# main/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import UserProfile, Address
import random
from datetime import timedelta
from django.utils import timezone
import re
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import LoginAttempt, ProductReview
import os
User = get_user_model()
from .models import SupportTicket

class UserRegisterForm(forms.ModelForm):
    ACCOUNT_TYPE_CHOICES = [
        ('individual', 'Физическое лицо'),
        ('legal', 'Юридическое лицо'),
    ]
    
    account_type = forms.ChoiceField(
        choices=ACCOUNT_TYPE_CHOICES,
        label='Тип аккаунта*',
        widget=forms.RadioSelect(attrs={'class': 'account-type-selector'})
    )
    
    first_name = forms.CharField(
        max_length=30, 
        required=False,
        label='Имя*',
        widget=forms.TextInput(attrs={'class': 'form-input individual-field'})
    )
    last_name = forms.CharField(
        max_length=30, 
        required=False,
        label='Фамилия*',
        widget=forms.TextInput(attrs={'class': 'form-input individual-field'})
    )
    
    company_name = forms.CharField(
        max_length=255, 
        required=False,
        label='Название компании*',
        widget=forms.TextInput(attrs={'class': 'form-input legal-field'})
    )
    inn = forms.CharField(
        max_length=12, 
        required=False,
        label='ИНН*',
        widget=forms.TextInput(attrs={'class': 'form-input legal-field', 'data-mask': 'inn'})
    )
    kpp = forms.CharField(
        max_length=9, 
        required=False,
        label='КПП',
        widget=forms.TextInput(attrs={'class': 'form-input legal-field', 'data-mask': 'kpp'})
    )
    ogrn = forms.CharField(
        max_length=13, 
        required=False,
        label='ОГРН',
        widget=forms.TextInput(attrs={'class': 'form-input legal-field', 'data-mask': 'ogrn'})
    )
    legal_address = forms.CharField(
        required=False,
        label='Юридический адрес*',
        widget=forms.Textarea(attrs={'class': 'form-input legal-field', 'rows': 3})
    )
    bank_name = forms.CharField(
        max_length=255, 
        required=False,
        label='Банк',
        widget=forms.TextInput(attrs={'class': 'form-input legal-field'})
    )
    bik = forms.CharField(
        max_length=9, 
        required=False,
        label='БИК',
        widget=forms.TextInput(attrs={'class': 'form-input legal-field', 'data-mask': 'bik'})
    )
    settlement_account = forms.CharField(
        max_length=20, 
        required=False,
        label='Расчетный счет',
        widget=forms.TextInput(attrs={'class': 'form-input legal-field', 'data-mask': 'account'})
    )
    correspondent_account = forms.CharField(
        max_length=20, 
        required=False,
        label='Корреспондентский счет',
        widget=forms.TextInput(attrs={'class': 'form-input legal-field', 'data-mask': 'correspondent'})
    )
    
    username = forms.CharField(
        max_length=150,
        label='Имя пользователя*',
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    email = forms.EmailField(
        label='Email*',
        widget=forms.EmailInput(attrs={'class': 'form-input'})
    )
    password1 = forms.CharField(
        label='Пароль*',
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
        help_text='Пароль должен содержать минимум 8 символов, заглавные и строчные буквы, цифры.'
    )
    password2 = forms.CharField(
        label='Подтверждение пароля*',
        widget=forms.PasswordInput(attrs={'class': 'form-input'})
    )
    agree_terms = forms.BooleanField(
        required=True,
        label='Я соглашаюсь с условиями использования'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'agree_terms', 
                 'account_type', 'company_name', 'inn', 'kpp', 'ogrn', 'legal_address', 
                 'bank_name', 'bik', 'settlement_account', 'correspondent_account']

    def clean(self):
        cleaned_data = super().clean()
        account_type = cleaned_data.get('account_type')
        
        if account_type == 'individual':
            if not cleaned_data.get('first_name'):
                self.add_error('first_name', 'Это поле обязательно для физических лиц')
            if not cleaned_data.get('last_name'):
                self.add_error('last_name', 'Это поле обязательно для физических лиц')
                
        elif account_type == 'legal':
            required_fields = {
                'company_name': 'Название компании обязательно',
                'inn': 'ИНН обязателен',
                'legal_address': 'Юридический адрес обязателен'
            }
            
            for field, error_message in required_fields.items():
                if not cleaned_data.get(field):
                    self.add_error(field, error_message)
            
            inn = cleaned_data.get('inn')
            if inn:
                if len(inn) not in [10, 12]:
                    self.add_error('inn', 'ИНН должен содержать 10 или 12 цифр')
                elif not inn.isdigit():
                    self.add_error('inn', 'ИНН должен содержать только цифры')
        
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Пароли не совпадают')
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        
        if commit:
            user.save()
            
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.account_type = self.cleaned_data['account_type']
            
            if self.cleaned_data['account_type'] == 'legal':
                profile.company_name = self.cleaned_data.get('company_name', '')
                profile.inn = self.cleaned_data.get('inn', '')
                profile.kpp = self.cleaned_data.get('kpp', '')
                profile.ogrn = self.cleaned_data.get('ogrn', '')
                profile.legal_address = self.cleaned_data.get('legal_address', '')
                profile.bank_name = self.cleaned_data.get('bank_name', '')
                profile.bik = self.cleaned_data.get('bik', '')
                profile.settlement_account = self.cleaned_data.get('settlement_account', '')
                profile.correspondent_account = self.cleaned_data.get('correspondent_account', '')
            
            profile.save()
        
        return user

class PhoneVerificationForm(forms.Form):
    phone = forms.CharField(
        max_length=20, 
        label='Номер телефона',
        widget=forms.TextInput(attrs={'placeholder': '+7 (999) 123-45-67'})
    )

class SMSCodeForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        label='Код из SMS',
        widget=forms.TextInput(attrs={'placeholder': '123456'})
    )

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone', 'date_of_birth', 'avatar', 'company', 'position']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'phone': forms.TextInput(attrs={'placeholder': '+7 (XXX) XXX-XX-XX'}),
            'company': forms.TextInput(attrs={'placeholder': 'Название компании'}),
            'position': forms.TextInput(attrs={'placeholder': 'Ваша должность'}),
        }
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            phone = ''.join(filter(str.isdigit, phone))
            if len(phone) not in [10, 11]:
                raise forms.ValidationError("Введите корректный номер телефона")
        return phone
    
class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['full_name', 'phone', 'city', 'address', 'postal_code', 'is_default']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'ФИО получателя'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Телефон для связи'}),
            'city': forms.TextInput(attrs={'placeholder': 'Город'}),
            'address': forms.Textarea(attrs={'placeholder': 'Полный адрес доставки', 'rows': 3}),
            'postal_code': forms.TextInput(attrs={'placeholder': 'Почтовый индекс'}),
        }
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            phone = ''.join(filter(str.isdigit, phone))
            if len(phone) not in [10, 11]:
                raise forms.ValidationError("Введите корректный номер телефона")
        return phone
    
class SecureUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    agree_terms = forms.BooleanField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'agree_terms']
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с таким email уже существует.')
        return email
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        
        if len(password1) < 6:  
            raise ValidationError('Пароль должен содержать минимум 6 символов.')
        
        # if not re.search(r'[A-Z]', password1):
        #     raise ValidationError('Пароль должен содержать хотя бы одну заглавную букву.')
        
        if not re.search(r'[a-z]', password1):
            raise ValidationError('Пароль должен содержать хотя бы одну строчную букву.')
        
        # if not re.search(r'\d', password1):
        #     raise ValidationError('Пароль должен содержать хотя бы одну цифру.')
        
        # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password1):
        #     raise ValidationError('Пароль должен содержать хотя бы один специальный символ.')
        
        # Проверка на распространенные пароли
        common_passwords = ['password', '123456', 'qwerty', 'admin']
        if password1.lower() in common_passwords:
            raise ValidationError('Этот пароль слишком распространен. Выберите другой.')
        
        return password1
    
class SecureAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='Имя пользователя или Email',
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Введите имя пользователя или email'})
    )
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        ip_address = self.get_client_ip()
        
        if LoginAttempt.is_ip_blocked(ip_address):
            raise ValidationError(
                'Слишком много неудачных попыток входа. Попробуйте через 15 минут.'
            )
        
        if username and password:
            try:
                user_by_username = User.objects.get(username=username)
                username = user_by_username.username  
            except User.DoesNotExist:
                try:
                    user_by_email = User.objects.get(email=username)
                    username = user_by_email.username 
                except User.DoesNotExist:
                    pass
            
            self.cleaned_data['username'] = username
            
            try:
                user = User.objects.get(username=username)
                if not user.is_active:
                    raise ValidationError('Аккаунт заблокирован. Свяжитесь с поддержкой.')
            except User.DoesNotExist:
                pass
        
        return super().clean()
    
    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

class SecurePasswordResetForm(forms.Form):
    email = forms.EmailField()
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if not User.objects.filter(email=email, is_active=True).exists():
            # Для безопасности не сообщаем, что email не найден
            pass
        return email

class SecureSetPasswordForm(forms.Form):
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)
    
    def clean_password1(self):
        # Та же логика проверки пароля, что и в SecureUserCreationForm
        password1 = self.cleaned_data.get('password1')
        
        if len(password1) < 6:
            raise ValidationError('Пароль должен содержать минимум 6 символов.')
        
        # if not re.search(r'[A-Z]', password1):
        #     raise ValidationError('Пароль должен содержать хотя бы одну заглавную букву.')
        
        if not re.search(r'[a-z]', password1):
            raise ValidationError('Пароль должен содержать хотя бы одну строчную букву.')
        
        # if not re.search(r'\d', password1):
        #     raise ValidationError('Пароль должен содержать хотя бы одну цифру.')
        
        # `if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password1):
        #     raise ValidationError('Пароль должен содержать хотя бы один специальный символ.')`
        
        return password1
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError('Пароли не совпадают.')
        
        return cleaned_data

class ProductReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=ProductReview.RATING_CHOICES,
        widget=forms.RadioSelect,
        label='Оценка'
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Расскажите о вашем опыте использования товара...',
            'maxlength': '1000'
        }),
        label='Комментарий',
        help_text='Максимум 1000 символов'
    )
    
    class Meta:
        model = ProductReview
        fields = ['rating', 'comment']
    
    def clean_comment(self):
        comment = self.cleaned_data.get('comment', '').strip()
        if len(comment) < 10:
            raise forms.ValidationError('Комментарий должен содержать минимум 10 символов')
        return comment
    
    def save(self, commit=True):
        review = super().save(commit=False)
        review.is_moderated = False
        review.is_approved = False
        
        if commit:
            review.save()
        return review
    
class SupportTicketForm(forms.ModelForm):
    attachments = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(),
        label='Прикрепить файл'
    )
    
    class Meta:
        model = SupportTicket
        fields = ['subject', 'description', 'priority']