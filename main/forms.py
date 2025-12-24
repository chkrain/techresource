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
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox
from .models import SupportTicket, UserProfile
from .validators import validate_avatar, validate_profile_background

class ReCaptchaFieldV2(ReCaptchaField):
    widget = ReCaptchaV2Checkbox

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.attrs.update({
            'data-theme': 'light',
            'data-size': 'normal',
        })

class UserRegisterForm(forms.ModelForm):
    captcha = ReCaptchaField(
        widget=ReCaptchaV2Checkbox(
            attrs={
                'data-theme': 'light',
                'data-size': 'normal',
            }
        ),
        label='',
        error_messages={'required': 'Пожалуйста, подтвердите, что вы не робот'}
    )
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
    """Расширенная форма профиля"""
    
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Имя'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Фамилия'
        })
    )
    
    avatar = forms.ImageField(
        required=False,
        validators=[validate_avatar],
        widget=forms.FileInput(attrs={
            'class': 'form-input',
            'accept': 'image/*'
        }),
        help_text='JPEG, PNG, GIF, WebP (макс. 5MB, мин. 100x100px)'
    )
    
    remove_avatar = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        }),
        label='Удалить аватар'
    )
    
    public_bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 4,
            'placeholder': 'Расскажите о себе...',
            'maxlength': '1000'
        }),
        help_text='Максимум 1000 символов'
    )
    
    public_skills = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Навыки через запятую'
        })
    )
    
    privacy_mode = forms.ChoiceField(
        choices=UserProfile.PRIVACY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Кто может видеть ваш профиль'
    )
    
    profile_theme = forms.ChoiceField(
        choices=[
            ('default', 'По умолчанию'),
            ('dark', 'Темная'),
            ('light', 'Светлая'),
            ('blue', 'Синяя'),
            ('green', 'Зеленая'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    profile_background = forms.ImageField(
        required=False,
        validators=[validate_profile_background],
        widget=forms.FileInput(attrs={
            'class': 'form-input',
            'accept': 'image/*'
        }),
        help_text='JPEG, PNG, WebP (макс. 10MB, мин. 800x400px)'
    )
    
    remove_background = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        }),
        label='Удалить фон'
    )
    
    class Meta:
        model = UserProfile
        fields = [
            'first_name', 'last_name', 'phone', 'company', 'position',
            'avatar', 'remove_avatar', 'profile_background', 'remove_background',
            'public_bio', 'public_skills', 'privacy_mode', 'profile_theme',
            'show_statistics', 'show_recent_activity' 
        ]
        widgets = {
            'public_bio': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 4,
                'maxlength': '1000'
            }),
            'public_skills': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Навыки через запятую'
            }),
            'privacy_mode': forms.Select(attrs={'class': 'form-select'}),
            'profile_theme': forms.Select(attrs={'class': 'form-select'}),
            'avatar': forms.FileInput(attrs={
                'class': 'form-input',
                'accept': 'image/*'
            }),
            'profile_background': forms.FileInput(attrs={
                'class': 'form-input', 
                'accept': 'image/*'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
    
    def clean_public_bio(self):
        """Очистка публичной биографии"""
        bio = self.cleaned_data.get('public_bio', '')
        
        from django.utils.html import strip_tags
        clean_bio = strip_tags(bio)
        
        if len(clean_bio) > 1000:
            raise forms.ValidationError('Биография не должна превышать 1000 символов')
        
        return clean_bio
    
    def clean_public_skills(self):
        """Очистка навыков"""
        skills = self.cleaned_data.get('public_skills', '')
        
        skills_list = [skill.strip() for skill in skills.split(',') if skill.strip()]
        
        if len(skills_list) > 20:
            raise forms.ValidationError('Максимум 20 навыков')
        
        for skill in skills_list:
            if len(skill) > 50:
                raise forms.ValidationError(f'Навык "{skill[:20]}..." слишком длинный (макс. 50 символов)')
        
        return ', '.join(skills_list)
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        if 'first_name' in self.cleaned_data:
            profile.user.first_name = self.cleaned_data['first_name']
        if 'last_name' in self.cleaned_data:
            profile.user.last_name = self.cleaned_data['last_name']
        
        if self.cleaned_data.get('remove_avatar'):
            if profile.avatar:
                profile.avatar.delete(save=False)
                profile.avatar = None
            if profile.avatar_small:
                profile.avatar_small.delete(save=False)
                profile.avatar_small = None
            if profile.avatar_medium:
                profile.avatar_medium.delete(save=False)
                profile.avatar_medium = None
            if profile.avatar_large:
                profile.avatar_large.delete(save=False)
                profile.avatar_large = None
        
        if self.cleaned_data.get('remove_background') and profile.profile_background:
            profile.profile_background.delete(save=False)
            profile.profile_background = None
        
        if commit:
            profile.user.save()
            profile.save()
        
        return profile

    
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
    captcha = ReCaptchaField(
        widget=ReCaptchaV2Checkbox(
            attrs={
                'data-theme': 'light',
                'data-size': 'normal',
            }
        ),
        label='',
        error_messages={'required': 'Пожалуйста, подтвердите, что вы не робот'}
    )
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
    captcha = ReCaptchaField(
        widget=ReCaptchaV2Checkbox(
            attrs={
                'data-theme': 'light',
                'data-size': 'normal',
            }
        ),
        label='',
        error_messages={'required': 'Пожалуйста, подтвердите, что вы не робот'}
    )
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
    
    captcha = ReCaptchaField(
        widget=ReCaptchaV2Checkbox(
            attrs={
                'data-theme': 'light',
                'data-size': 'normal',
            }
        ),
        label='',
        error_messages={'required': 'Пожалуйста, подтвердите, что вы не робот'}
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        if not User.objects.filter(email=email, is_active=True).exists():
            pass
        return email

class SecureSetPasswordForm(forms.Form):
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)
    
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
    captcha = ReCaptchaField(
        widget=ReCaptchaV2Checkbox(
            attrs={
                'data-theme': 'light',
                'data-size': 'normal',
            }
        ),
        label='',
        error_messages={'required': 'Пожалуйста, подтвердите, что вы не робот'}
    )
    attachments = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(),
        label='Прикрепить файл'
    )
    
    class Meta:
        model = SupportTicket
        fields = ['subject', 'description', 'priority']

class AdminProfileTagsForm(forms.ModelForm):
    """Форма для админов - управление тегами профиля"""
    
    class Meta:
        model = UserProfile
        fields = ['profile_tags', 'is_verified', 'verification_badge']
        widgets = {
            'profile_tags': forms.CheckboxSelectMultiple(
                choices=UserProfile.PROFILE_TAGS
            ),
            'verification_badge': forms.Select(choices=[
                ('', 'Нет бейджа'),
                ('premium', '⭐ Премиум'),
                ('trusted', '✅ Проверенный'),
                ('expert', '👨‍💼 Эксперт'),
                ('founder', '🚀 Основатель'),
            ])
        }

class PrivacySettingsForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'privacy_mode',
            'email_visibility',
            'phone_visibility',
            'company_visibility',
            'position_visibility',
            'skills_visibility',
            'activity_visibility',
        ]
        widgets = {
            field: forms.RadioSelect(attrs={'class': 'privacy-radio'})
            for field in fields
        }