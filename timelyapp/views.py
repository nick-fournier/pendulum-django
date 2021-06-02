from django.shortcuts import redirect
from django.urls import reverse_lazy
from rest_framework.permissions import AllowAny
from rest_framework import viewsets

from .serializers import *
from .forms import *
from timelyapp.utils import get_business_id


# Create your views here.
def redirect_view(request):
    response = redirect('/api/')
    return response

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
    queryset = Invoice.objects.all().order_by('-pk')
    success_url = reverse_lazy('home')

    # Overrides the internal function
    def get_queryset(self):
        queryset = self.queryset
        business_id = get_business_id(self.request.user.id)
        query_set = queryset.filter(bill_to__id=business_id)
        return query_set


class ReceivablesViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.all().order_by('-pk')
    success_url = reverse_lazy('home')

    # Overrides the internal function
    def get_queryset(self):
        queryset = self.queryset
        business_id = get_business_id(self.request.user.id)
        query_set = queryset.filter(bill_from__id=business_id)
        return query_set

class NewsletterViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = NewsletterSerializer
    queryset = Newsletter.objects.none()
    success_url = reverse_lazy('home')
