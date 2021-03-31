from django.shortcuts import render, redirect
from django.core.mail import send_mail, BadHeaderError
from django.http import HttpResponse
# from django.contrib.auth.forms import PasswordResetForm, UserCreationForm
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.db.models.query_utils import Q
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib import messages #import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views import generic
from django.views.generic.edit import CreateView
from django.views.generic import ListView
from django.urls import reverse_lazy
from .models import CustomUser, Invoice, Business, PurchaseOrder
from .forms import CreateInvoice, CustomUserCreationForm, CustomPasswordResetForm

import pandas as pd
import json

# Create your views here.
def index(request):
    return render(request, "home.html")

def password_reset_request(request):
    if request.method == "POST":
        password_reset_form = CustomPasswordResetForm(request.POST)
        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data['email']
            associated_users = CustomUser.objects.filter(Q(email=data))
            if associated_users.exists():
                for user in associated_users:
                    subject = "Password Reset Requested"
                    email_template_name = "registration/password_reset_email.txt"
                    c = {
                        "email": user.email,
                        'domain': '127.0.0.1:8000',
                        'site_name': 'Timely',
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "user": user,
                        'token': default_token_generator.make_token(user),
                        'protocol': 'http',
                    }
                    email = render_to_string(email_template_name, c)
                    try:
                        send_mail(subject, email, 'admin@timely.com', [user.email], fail_silently=False)
                    except BadHeaderError:
                        return HttpResponse('Invalid header found.')
                    # messages.success(request, 'A message with reset password instructions has been sent to your inbox.')
                    # return redirect("timelyapp:index")
                    return redirect("/password_reset/done/")
                # messages.error(request, 'An invalid email has been entered.')
    password_reset_form = CustomPasswordResetForm()
    return render(request=request,
                  template_name="registration/password_reset_form.html",
                  context={"password_reset_form": password_reset_form})

class SignUpView(generic.CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'


class NewInvoiceView(CreateView):
    model = Invoice
    form_class = CreateInvoice
    template_name = 'invoices/new_invoice.html'
    success_url = reverse_lazy('dashboard')


class DashboardView(ListView):
    template_name = 'invoices/dashboard.html'
    success_url = reverse_lazy('home')
    queryset = Business.objects.all()


class ReceivablesView(ListView):
    template_name = 'invoices/receivables.html'
    success_url = reverse_lazy('home')
    queryset = Business.objects.all()

    def get_context_data(self, **kwargs):
        context = super(ReceivablesView, self).get_context_data(**kwargs)
        biz_id = Business.objects.filter(owner__id=self.request.user.id).values_list('id', flat=True)[0]
        invoices = Invoice.objects.filter(bill_to__id=biz_id).values()

        if invoices.exists():
            billed_business = Business.objects.filter(pk=invoices[0]['bill_to_id']).values()
            # purchase_order = PurchaseOrder.objects.filter(invoice=invoices[0]['id']).values()

            invoices = pd.DataFrame(invoices).rename(columns={'id': 'invoice_id'})
            billed_business = pd.DataFrame(billed_business).rename(columns={'id': 'business_id'})

            df = invoices.merge(billed_business,
                                left_on='bill_to_id',
                                right_on='business_id')

            df.total_price = '$' + df.total_price.astype('float').round(2).to_string(index=False)
            df['date_sent'] = [x.strftime("%B %d, %Y").lstrip("0") for x in df['date_sent']]
            df['date_due'] = [x.strftime("%B %d, %Y").lstrip("0") for x in df['date_due']]
            df = df.sort_values('date_due', ascending=False).reset_index(drop=True)
            df.index += 1

            # parsing the DataFrame in json format.
            json_records = df.reset_index().to_json(orient='records')
            data = list(json.loads(json_records))
            context['receivables'] = data
            return context

class PayablesView(ListView):
    template_name = 'invoices/payables.html'
    success_url = reverse_lazy('home')
    queryset = Business.objects.all()

    def get_context_data(self, **kwargs):
        context = super(PayablesView, self).get_context_data(**kwargs)
        biz_id = Business.objects.filter(owner__id=self.request.user.id).values_list('id', flat=True)[0]
        invoices = Invoice.objects.filter(bill_from__id=biz_id).values()

        if invoices.exists():
            owed_business = Business.objects.filter(pk=invoices[0]['bill_from_id']).values()
            invoices = pd.DataFrame(invoices).rename(columns={'id': 'invoice_id'})
            billed_business = pd.DataFrame(owed_business).rename(columns={'id': 'business_id'})

            df = invoices.merge(billed_business,
                                left_on='bill_from_id',
                                right_on='business_id')

            df.total_price = '$' + df.total_price.astype('float').round(2).to_string(index=False)
            df['date_sent'] = [x.strftime("%B %d, %Y").lstrip("0") for x in df['date_sent']]
            df['date_due'] = [x.strftime("%B %d, %Y").lstrip("0") for x in df['date_due']]
            df = df.sort_values('date_due', ascending=False).reset_index(drop=True)
            df.index += 1

            # parsing the DataFrame in json format.
            json_records = df.reset_index().to_json(orient='records')
            data = list(json.loads(json_records))
            context['payables'] = data
            return context