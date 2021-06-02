from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordResetForm
from django.forms import ModelForm

from .models import *

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm):
        model = CustomUser
        fields = ('email',)

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('email',)

class CustomPasswordResetForm(PasswordResetForm):
    class Meta:
        model = CustomUser
        fields = ('email',)

class CreateBusinessForm(ModelForm):
    class Meta:
        model = Business
        fields = ['business_name', 'billing_address', 'shipping_address']
