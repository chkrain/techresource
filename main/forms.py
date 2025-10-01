# main/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile, Address

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    phone = forms.CharField(max_length=20, required=False, label="Телефон")
    company = forms.CharField(max_length=200, required=False, label="Компания")
    position = forms.CharField(max_length=100, required=False, label="Должность")
    
    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'company', 'position', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Создаем или получаем профиль и обновляем данные
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.phone = self.cleaned_data['phone']
            profile.company = self.cleaned_data['company']
            profile.position = self.cleaned_data['position']
            profile.save()
        return user

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone', 'company', 'position']

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['title', 'full_name', 'phone', 'address', 'city', 'postal_code', 'is_default']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }