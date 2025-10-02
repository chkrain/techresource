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
from .models import LoginAttempt

User = get_user_model()

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False, label='Телефон')

    class Meta:
        model = User  # Используем кастомного пользователя
        fields = ['username', 'email', 'phone', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile = UserProfile.objects.get_or_create(
                user=user,
                defaults={'phone': self.cleaned_data.get('phone')}
            )
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
        fields = ['phone', 'date_of_birth', 'avatar']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'phone': forms.TextInput(attrs={'placeholder': '+7 (XXX) XXX-XX-XX'}),
        }
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # Basic phone validation
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
        
        # Упрощенная проверка пароля (можно закомментировать для тестирования)
        if len(password1) < 8:  # Уменьшили с 10 до 8
            raise ValidationError('Пароль должен содержать минимум 8 символов.')
        
        # Опциональные проверки (можно закомментировать)
        if not re.search(r'[A-Z]', password1):
            raise ValidationError('Пароль должен содержать хотя бы одну заглавную букву.')
        
        if not re.search(r'[a-z]', password1):
            raise ValidationError('Пароль должен содержать хотя бы одну строчную букву.')
        
        if not re.search(r'\d', password1):
            raise ValidationError('Пароль должен содержать хотя бы одну цифру.')
        
        # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password1):
        #     raise ValidationError('Пароль должен содержать хотя бы один специальный символ.')
        
        # Проверка на распространенные пароли
        common_passwords = ['password', '123456', 'qwerty', 'admin']
        if password1.lower() in common_passwords:
            raise ValidationError('Этот пароль слишком распространен. Выберите другой.')
        
        return password1
    
class SecureAuthenticationForm(AuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        # Получаем IP-адрес
        ip_address = self.get_client_ip()
        
        # Проверяем, не заблокирован ли IP
        if LoginAttempt.is_ip_blocked(ip_address):
            raise ValidationError(
                'Слишком много неудачных попыток входа. Попробуйте через 15 минут.'
            )
        
        # Убираем проверку email_verified, так как у стандартной модели User нет этого поля
        if username and password:
            try:
                user = User.objects.get(username=username)
                
                # Проверяем, не заблокирован ли аккаунт
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
        
        if len(password1) < 10:
            raise ValidationError('Пароль должен содержать минимум 10 символов.')
        
        if not re.search(r'[A-Z]', password1):
            raise ValidationError('Пароль должен содержать хотя бы одну заглавную букву.')
        
        if not re.search(r'[a-z]', password1):
            raise ValidationError('Пароль должен содержать хотя бы одну строчную букву.')
        
        if not re.search(r'\d', password1):
            raise ValidationError('Пароль должен содержать хотя бы одну цифру.')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password1):
            raise ValidationError('Пароль должен содержать хотя бы один специальный символ.')
        
        return password1
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError('Пароли не совпадают.')
        
        return cleaned_data
