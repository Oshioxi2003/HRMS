from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from accounts.models import *


User = get_user_model()

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email đã tồn tại.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_active = True  # Set user as active by default
        user.status = 'Active'  # Set status as Active
        if commit:
            user.save()
        return user
    


class CustomUserCreationForm(forms.ModelForm):
    """Form for creating a new user"""
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user

class CustomUserChangeForm(forms.ModelForm):
    """Form for updating an existing user"""
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'role']


class PermissionForm(forms.ModelForm):
    class Meta:
        model = Permission
        fields = ['role', 'module', 'access_right']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'module': forms.TextInput(attrs={'class': 'form-control'}),
            'access_right': forms.Select(attrs={'class': 'form-control'}),
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password and new_password != confirm_password:
            self.add_error('confirm_password', 'Mật khẩu không khớp.')
        
        return cleaned_data
