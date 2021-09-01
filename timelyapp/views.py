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
        queryset = self.queryset

        try:
            queryset = Business.objects.filter(id=get_business_id(self.request.user.id))
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
        business_id = get_business_id(self.request.user.id)
        queryset = Invoice.objects.filter(Q(bill_from__id=business_id) | Q(bill_to__id=business_id)).order_by('id')
        return queryset

class NewReceivableViewSet(viewsets.ModelViewSet):
    serializer_class = NewReceivableSerializer
    queryset = []

    # def get_queryset(self):
    #     business_id = get_business_id(self.request.user.id)
    #     queryset = Invoice.objects.filter(bill_from__id=business_id)
    #     return queryset

class NewPayableViewSet(viewsets.ModelViewSet):
    serializer_class = NewPayableSerializer
    queryset = []

    # def get_queryset(self):
    #     business_id = get_business_id(self.request.user.id)
    #     queryset = Invoice.objects.filter(bill_to__id=business_id)
    #     return queryset

class BusinessViewSet(viewsets.ModelViewSet):
    serializer_class = BusinessSerializer
    queryset = Business.objects.all()

class InventoryViewSet(viewsets.ModelViewSet):
    serializer_class = InventorySerializer

    def get_queryset(self):
        business_id = get_business_id(self.request.user.id)
        queryset = Inventory.objects.filter(Q(business__id=business_id)).order_by('last_updated')
        return queryset

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer

    def get_queryset(self):
        business_id = get_business_id(self.request.user.id)
        item_list = Inventory.objects.filter(Q(business__id=business_id)).values_list('id', flat=True)
        queryset = Order.objects.filter(pk__in=item_list)
        return queryset

class PayablesViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    success_url = reverse_lazy('home')

    # Overrides the internal function
    def get_queryset(self):
        business_id = get_business_id(self.request.user.id)
        queryset = Invoice.objects.filter(bill_to__id=business_id).order_by('date_due')
        return queryset

class ReceivablesViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    success_url = reverse_lazy('home')

    # Overrides the internal function
    def get_queryset(self):
        business_id = get_business_id(self.request.user.id)
        queryset = Invoice.objects.filter(bill_from__id=business_id).order_by('date_due')
        return queryset

class OutreachViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = OutreachSerializer
    queryset = Outreach.objects.none()
    success_url = reverse_lazy('home')
    throttle_scope = 'outreach'

