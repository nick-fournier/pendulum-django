from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordResetForm
from django.forms import ModelForm, modelformset_factory
from django.forms.models import inlineformset_factory
from django.forms import formset_factory

from django import forms
from .custom_layout_object import *
from .models import *
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, Div, HTML, ButtonHolder, Submit

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
        fields = ['business_name', 'address']

class CreateOrderForm(ModelForm):
    class Meta:
        model = Order
        fields = ['item', 'quantity_purchased', 'discount_code']

OrderFormSet = inlineformset_factory(
    Invoice, Order, form=CreateOrderForm,
    fields=['item', 'quantity_purchased', 'discount_code'], extra=1, can_delete=True
    )


class CreateInvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['bill_to', 'terms']

    def __init__(self, *args, **kwargs):
        super(CreateInvoiceForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = True
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3 create-label'
        self.helper.field_class = 'col-md-9'
        self.helper.layout = Layout(
            Div(
                Field('bill_to'),
                Field('terms'),
                Fieldset('Add orders',
                    Formset('item')),
                HTML("<br>"),
                ButtonHolder(Submit('submit', 'save')),
                )
            )