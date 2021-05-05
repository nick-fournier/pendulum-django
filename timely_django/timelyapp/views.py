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
from timelyapp.utils import get_business_id

import pandas as pd
import json
import datetime
import numpy as np

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
class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FullInvoiceSerializer
    queryset = Invoice.objects.all()

    def get_queryset(self):
        queryset = self.queryset
        business_id = get_business_id(self.request.user.id)
        query_set = queryset.filter(Q(bill_from__id=business_id) | Q(bill_to__id=business_id)).order_by('id')
        return query_set

# Django REST framework endpoints
class NewInvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = NewInvoiceSerializer
    queryset = Invoice.objects.all()

    def get_queryset(self):
        queryset = self.queryset
        business_id = get_business_id(self.request.user.id)
        query_set = queryset.filter(bill_from__id=business_id)
        return query_set


class BusinessViewSet(viewsets.ModelViewSet):
    serializer_class = BusinessSerializer
    queryset = Business.objects.all()


class InventoryViewSet(viewsets.ModelViewSet):
    serializer_class = InventorySerializer
    queryset = Inventory.objects.all()

    def get_queryset(self):
        queryset = self.queryset
        business_id = get_business_id(self.request.user.id)
        query_set = queryset.filter(Q(business__id=business_id)).order_by('last_updated')
        return query_set


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()

    def get_queryset(self):
        queryset = self.queryset
        business_id = get_business_id(self.request.user.id)
        item_list = Inventory.objects.filter(Q(business__id=business_id)).values_list('id', flat=True)
        query_set = queryset.filter(pk__in=item_list)
        return query_set


class PayablesViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.all()
    success_url = reverse_lazy('home')

    # Overrides the internal function
    def get_queryset(self):
        queryset = self.queryset
        business_id = get_business_id(self.request.user.id)
        query_set = queryset.filter(bill_to__id=business_id)
        return query_set


class ReceivablesViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.all()
    success_url = reverse_lazy('home')

    # Overrides the internal function
    def get_queryset(self):
        queryset = self.queryset
        business_id = get_business_id(self.request.user.id)
        query_set = queryset.filter(bill_from__id=business_id)
        return query_set


#
# #### OLD FORMS BELOW THIS, MARKED FOR DELETION ####
# class NewBusinessFormView(CreateView):
#     model = Business
#     template_name = 'registration/new_business.html'
#     form_class = CreateBusinessForm
#     success_url = reverse_lazy('home')
#
#     def form_valid(self, form):
#         form.instance.owner = self.request.user
#         return super().form_valid(form)
#
# # Nested Invoice Form
# class NewInvoiceFormView(CreateView):
#     model = Invoice
#     template_name = 'invoices/new_invoice.html'
#     form_class = CreateInvoiceForm
#     success_url = None
#
#     #Use this to have useful default fields
#     def get_initial(self):
#         pass
#
#     def get_context_data(self, **kwargs):
#         data = super(NewInvoiceFormView, self).get_context_data(**kwargs)
#         if self.request.POST:
#             data['item'] = OrderFormSet(self.request.POST)
#         else:
#             data['item'] = OrderFormSet()
#         return data
#
#     def form_valid(self, form):
#         context = self.get_context_data()
#         item = context['item']
#
#         with transaction.atomic():
#             form.instance.bill_from = Business.objects.get(owner__id=self.request.user.id)
#             form.instance.date_sent = datetime.date.today().strftime("%Y-%m-%d")
#             form.instance.date_due = calculate_duedate(form.instance.terms)
#
#             self.object = form.save()
#             if item.is_valid():
#                 item.instance = self.object
#                 item.save()
#         return super(NewInvoiceFormView, self).form_valid(form)
#
#     def get_success_url(self):
#         return reverse_lazy('dashboard')
#
#
#
# # # old inbox views (can delete later)
# class ReceivablesView(ListView):
#     template_name = 'invoices/receivables.html'
#     success_url = reverse_lazy('home')
#     queryset = Business.objects.all()
#
#     def get_context_data(self, **kwargs):
#         context = super(ReceivablesView, self).get_context_data(**kwargs)
#         business_id = Business.objects.filter(owner__id=self.request.user.id).values()[0]['id']
#         context['receivables'] = get_invoices(business_id, 'receivables')
#         return context
#
#
# class PayablesView(ListView):
#     template_name = 'invoices/payables.html'
#     success_url = reverse_lazy('home')
#     queryset = Business.objects.all()
#
#     def get_context_data(self, **kwargs):
#         context = super(PayablesView, self).get_context_data(**kwargs)
#         business_id = Business.objects.filter(owner__id=self.request.user.id).values()[0]['id']
#         context['payables'] = get_invoices(business_id, 'payables')
#         return context
#
#
# # Manual JSON serializer (can delete later)
# class ReceivablesJSONView(ListView):
#     template_name = 'invoices/receivables.html'
#     success_url = reverse_lazy('home')
#     queryset = Business.objects.all()
#
#     def get(self, *args, **kwargs):
#         business_id = Business.objects.filter(owner__id=self.request.user.id).values()[0]['id']
#         data = get_invoices(business_id, 'receivables')
#         return JsonResponse(data, safe=False)
#
# class PayablesJSONView(ListView):
#     template_name = 'invoices/payables.html'
#     success_url = reverse_lazy('home')
#     queryset = Business.objects.all()
#
#     def get(self, *args, **kwargs):
#         business_id = Business.objects.filter(owner__id=self.request.user.id).values()[0]['id']
#         data = get_invoices(business_id, 'payables')
#         return JsonResponse(data, safe=False)