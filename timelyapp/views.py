from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from .serializers import *
from .stripe_views import *
from timelyapp.utils import get_business_id

def chart_view(request):
    return render(request, 'chart.html')

# Create your views here.
def redirect_view(request):
    response = redirect('/api/')
    return response



class EmailVerifyView(viewsets.ReadOnlyModelViewSet):
    serializer_class = EmailVerifySerializer

    def get_queryset(self):
        return EmailAddress.objects.filter(user_id=self.request.user.id)

class BusinessInfo(viewsets.ModelViewSet):
    serializer_class = BusinessInfoSerializer

    def get_queryset(self):
        try:
            queryset = Business.objects.filter(id=self.request.user.business.id)
        except Business.DoesNotExist:
            queryset = []

        # Checking if data is current
        # account_info = stripe.Account.retrieve(queryset.get().stripe_act_id)
        # print(account_info)
        # print(queryset)

        return queryset

class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FullInvoiceSerializer

    def get_queryset(self):
        #business_id = get_business_id(self.request.user.id)
        business_id = self.request.user.business.id
        queryset = Invoice.objects.filter(Q(bill_from__id=business_id) | Q(bill_to__id=business_id)).order_by('id')
        return queryset

class NewReceivableViewSet(viewsets.ModelViewSet):
    serializer_class = NewReceivableSerializer

    def get_queryset(self):
        business_id = self.request.user.business.id
        queryset = Invoice.objects.filter(bill_from__id=business_id).order_by('date_due')
        return queryset

class NewPayableViewSet(viewsets.ModelViewSet):
    serializer_class = NewPayableSerializer

    def get_queryset(self):
        business_id = self.request.user.business.id
        queryset = Invoice.objects.filter(bill_to__id=business_id).order_by('date_due')
        return queryset

class BusinessViewSet(viewsets.ModelViewSet):
    serializer_class = BusinessSerializer
    queryset = Business.objects.all()

class InventoryViewSet(viewsets.ModelViewSet):
    serializer_class = InventorySerializer

    def get_queryset(self):
        print(self.request.user.business)
        business_id = self.request.user.business.id
        queryset = Inventory.objects.filter(Q(business__id=business_id)).order_by('last_updated')
        return queryset

class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer

    def get_queryset(self):
        business_id = self.request.user.business.id
        invoice_list = Invoice.objects.filter(bill_from__id=business_id)
        queryset = Order.objects.filter(invoice__in=invoice_list)
        return queryset

class PayablesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer
    success_url = reverse_lazy('home')

    def get_queryset(self):
        business_id = self.request.user.business.id
        queryset = Invoice.objects.filter(bill_to__id=business_id).order_by('date_due')
        return queryset

class ReceivablesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer
    success_url = reverse_lazy('home')

    def get_queryset(self):
        business_id = self.request.user.business.id
        queryset = Invoice.objects.filter(bill_from__id=business_id).order_by('date_due')
        return queryset

class OutreachViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = OutreachSerializer
    queryset = Outreach.objects.none()
    success_url = reverse_lazy('home')
    throttle_scope = 'outreach'

