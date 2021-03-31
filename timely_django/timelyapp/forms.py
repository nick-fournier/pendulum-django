from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordResetForm
from django.forms import ModelForm
from .models import CustomUser, Invoice

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


class CreateInvoice(ModelForm):

    class Meta:
        model = Invoice
        exclude = ['bill_from', 'currency']
        fields = '__all__'