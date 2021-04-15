from django.shortcuts import render, redirect
from django.core.mail import send_mail, BadHeaderError
from django.http import HttpResponse
from django.contrib.auth.tokens import default_token_generator
from django.db.models.query_utils import Q
from django.db import transaction
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.views import generic
from django.views.generic.edit import CreateView
from django.views.generic import ListView
from django.urls import reverse_lazy
from django.http import JsonResponse

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework import viewsets, serializers

from .serializers import *
from .models import *
from .forms import *

import pandas as pd
import json
import datetime
import numpy as np


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

def type_converter(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, datetime.datetime):
        return obj.__str__()

def get_invoices(biz_id, type):

    if type == "receivables":
        invoices = Invoice.objects.filter(bill_from__id=biz_id).values()
        opposite = "bill_to_id"

    elif type == "payables":
        invoices = Invoice.objects.filter(bill_to__id=biz_id).values()
        opposite = "bill_from_id"
    else:
        return None

    if invoices.exists():
        #Gets the other business's data
        other_business = Business.objects.filter(pk=invoices[0][opposite]).values()
        order = Order.objects.filter(invoice__in=invoices.values_list('id', flat=True)).values()

        #Convert to data frame to merge
        invoices = pd.DataFrame(invoices).rename(columns={'id': 'invoice_id'})
        other_business = pd.DataFrame(other_business).rename(columns={'id': 'business_id'})
        order = pd.DataFrame(order)

        invoices_merged = invoices.merge(other_business,
                            left_on=opposite,
                            right_on='business_id')

        #Some formatting fixes
        invoices_merged.total_price.fillna(0, inplace=True)
        invoices_merged.total_price = '$' + invoices_merged.total_price.astype('float').round(2).astype(str)
        invoices_merged.date_sent = [x.strftime("%B %d, %Y").lstrip("0") for x in invoices_merged.date_sent]
        invoices_merged.date_due = ['COD' if x is None else x.strftime("%B %d, %Y").lstrip("0") for x in invoices_merged.date_due]

        invoices_merged = invoices_merged.sort_values('date_due', ascending=False).reset_index(drop=True)
        # invoices_merged.set_index('invoice_id', inplace=True)

        #Convert to JSON
        data_dict_list = []
        for i in range(len(invoices_merged)):
            invoice_id = invoices_merged.iloc[i].invoice_id
            invoice_dict = invoices_merged.iloc[i]
            order_dict = order[order.invoice_id == invoice_id].to_dict(orient='records')
            data_dict_list.append({**invoice_dict, **{"order_list": order_dict}})

        #This parses it to make sure any weird data types are smoothed out
        data_json = json.dumps(data_dict_list, indent=4, default=type_converter)
        data = list(json.loads(data_json))

        return data


# Create your views here.
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

# Templates view
class SignUpView(generic.CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

class DashboardView(ListView):
    template_name = 'invoices/dashboard.html'
    success_url = reverse_lazy('home')
    queryset = Business.objects.all()


# Django REST framework endpoints
class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset
        business_id = Business.objects.get(owner__id=self.request.user.id).id
        query_set = queryset.filter(Q(bill_from__id=business_id) | Q(bill_to__id=business_id)).order_by('id')
        return query_set


class PayablesViewSet(viewsets.ModelViewSet):
    serializer_class = PayablesSerializer
    queryset = Invoice.objects.all()
    success_url = reverse_lazy('home')
    permission_classes = [IsAuthenticated]

    # def put(self, request, *args, **kwargs):
    #     return self.update(request, *args, **kwargs)


    # Overrides the internal function
    def get_queryset(self):
        queryset = self.queryset
        business_id = Business.objects.get(owner__id=self.request.user.id).id
        query_set = queryset.filter(bill_to__id=business_id)
        return query_set


class ReceivablesViewSet(viewsets.ModelViewSet):
    serializer_class = ReceivablesSerializer
    queryset = Invoice.objects.all()
    success_url = reverse_lazy('home')
    permission_classes = [IsAuthenticated]

    # Overrides the internal function
    def get_queryset(self):
        queryset = self.queryset
        business_id = Business.objects.get(owner__id=self.request.user.id).id
        query_set = queryset.filter(bill_from__id=business_id)
        return query_set

# New Nested Invoice Form
class NewBusinessFormView(CreateView):
    model = Business
    template_name = 'registration/new_business.html'
    form_class = CreateBusinessForm
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)



# New Nested Invoice Form
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



# # old inbox views (can delete later)
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


# Manual JSON serializer (can delete later)
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