from django.shortcuts import render, redirect
from django.core.mail import send_mail, BadHeaderError
from django.http import HttpResponse
# from django.contrib.auth.forms import PasswordResetForm, UserCreationForm
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.db.models.query_utils import Q
from django.db import transaction
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib import messages #import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views import generic
from django.views.generic.edit import CreateView
from django.views.generic import ListView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.core import serializers


from .models import *
from .forms import *

import pandas as pd
import json
import datetime



#Generic functions
def get_duedate(term):
    today = datetime.date.today()
    term_choices = {'COD': 'On delivery',
                    'CIA': today,
                    'NET7': today + datetime.timedelta(7),
                    'NET10': today + datetime.timedelta(10),
                    'NET30': today + datetime.timedelta(30),
                    'NET60': today + datetime.timedelta(60),
                    'NET90': today + datetime.timedelta(90),
                    'NET120': today + datetime.timedelta(120),
                    }

    return term_choices[term].strftime("%Y-%m-%d")

def get_invoices(biz_id, type):

    if type == "receivables":
        invoices = Invoice.objects.filter(bill_to__id=biz_id).values()
        dir = "bill_to_id"
    elif type == "payables":
        invoices = Invoice.objects.filter(bill_from__id=biz_id).values()
        dir = "bill_from_id"
    else:
        return None

    if invoices.exists():
        billed_business = Business.objects.filter(pk=invoices[0][dir]).values()
        # order = Order.objects.filter(invoice=invoices[0]['id']).values()

        invoices = pd.DataFrame(invoices).rename(columns={'id': 'invoice_id'})
        billed_business = pd.DataFrame(billed_business).rename(columns={'id': 'business_id'})

        df = invoices.merge(billed_business,
                            left_on=dir,
                            right_on='business_id')

        df.total_price.fillna(0, inplace=True)
        df.total_price = '$' + df.total_price.astype('float').round(2).astype(str)
        df.date_sent = [x.strftime("%B %d, %Y").lstrip("0") for x in df.date_sent]
        df.date_due = ['COD' if x is None else x.strftime("%B %d, %Y").lstrip("0") for x in df.date_due]

        df = df.sort_values('date_due', ascending=False).reset_index(drop=True)
        df.index += 1

        # parsing the DataFrame in json format.
        json_records = df.reset_index().to_json(orient='records')
        data = list(json.loads(json_records))

        return data

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
        business_id = Business.objects.filter(owner__id=self.request.user.id).values()[0]['id']
        context['receivables'] = get_invoices(business_id, 'receivables')
        return context

class PayablesView(ListView):
    template_name = 'invoices/payables.html'
    success_url = reverse_lazy('home')
    queryset = Business.objects.all()

    def get_context_data(self, **kwargs):
        context = super(PayablesView, self).get_context_data(**kwargs)
        business_id = Business.objects.filter(owner__id=self.request.user.id).values()[0]['id']
        context['payables'] = get_invoices(business_id, 'payables')
        return context

class ReceivablesJSONView(ListView):
    template_name = 'invoices/receivables.html'
    success_url = reverse_lazy('home')
    queryset = Business.objects.all()

    def get(self, *args, **kwargs):
        business_id = Business.objects.filter(owner__id=self.request.user.id).values()[0]['id']
        data = get_invoices(business_id, 'receivables')
        return JsonResponse(data, safe=False)

class PayablesJSONView(ListView):
    template_name = 'invoices/payables.html'
    success_url = reverse_lazy('home')
    queryset = Business.objects.all()

    def get(self, *args, **kwargs):
        business_id = Business.objects.filter(owner__id=self.request.user.id).values()[0]['id']
        data = get_invoices(business_id, 'payables')
        return JsonResponse(data, safe=False)


class NewInvoiceFormView(CreateView):
    model = Invoice
    template_name = 'invoices/new_invoice.html'
    form_class = CreateInvoiceForm
    success_url = None

    #Use this to have useful default fields
    def get_initial(self):
        pass

    def get_context_data(self, **kwargs):
        data = super(NewInvoiceFormView, self).get_context_data(**kwargs)
        if self.request.POST:
            data['item'] = OrderFormSet(self.request.POST)
        else:
            data['item'] = OrderFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        item = context['item']

        with transaction.atomic():
            form.instance.bill_from = Business.objects.get(owner__id=self.request.user.id)
            form.instance.date_sent = datetime.date.today().strftime("%Y-%m-%d")
            form.instance.date_due = get_duedate(form.instance.terms)

            self.object = form.save()
            if item.is_valid():
                item.instance = self.object
                item.save()
        return super(NewInvoiceFormView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('dashboard')
