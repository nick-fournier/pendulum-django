from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view
from rest_framework.response import Response
from decimal import Decimal
from .serializers import *
from .forms import *
from timelyapp.utils import get_business_id
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY
timely_rate = Decimal(0.001)

# Stripe views
@api_view(['POST'])
def stripe_pay_invoice(request):

    # Check if invoice exists
    try:
        invoice = Invoice.objects.get(pk=request.data['id'])
        business = Business.objects.get(business_name=invoice.bill_from)
        timely_fee = round(timely_rate * 100 * invoice.invoice_total_price) # Calculate our fee
    except Invoice.DoesNotExist:
        content = {'Bad invoice': 'No matching invoice ID in records'}
        return Response(content, status=status.HTTP_404_NOT_FOUND)

    # Extract request data
    data = request.data

    if 'payment_method_types' not in data:
        data['payment_method_types'] = ['card']

    if 'currency' not in data:
        data['currency'] = invoice.currency.lower()

    # Check if the current user has authority to pay
    if Business.objects.get(business_name=invoice.bill_to).id != get_business_id(request.user.id):
        content = {'Bad invoice': 'You are not authorized to pay this invoice'}
        return Response(content, status=status.HTTP_404_NOT_FOUND)

    # Check if other account is onboarded, if not we'll have to handle this somehow (hold money until they onboard?)
    if not stripe.Account.retrieve(business.stripe_id).charges_enabled:
        content = {'Bad invoice': 'Stripe account ' + business.stripe_id + ' for receivable is not fully onboarded.'}
        return Response(content, status=status.HTTP_404_NOT_FOUND)

    payment_intent = stripe.PaymentIntent.create(
        payment_method_types=data['payment_method_types'],
        amount=int(invoice.invoice_total_price*100),
        currency=data['currency'],
        # application_fee_amount=timely_fee,
        stripe_account=business.stripe_id,
    )
    return Response(status=status.HTTP_200_OK, data=payment_intent)

@api_view(['GET'])
def stripe_onboard(request):

    # Parse any data passed
    data = request.data
    if 'refresh_url' not in data:
        data['refresh_url'] = 'https://www.timelypay.app/invoices' # request.build_absolute_uri('/invoices/')
    if 'return_url' not in data:
        data['return_url'] = 'https://www.timelypay.app/invoices' # request.build_absolute_uri('/invoices/')

    # Query current business
    business = Business.objects.get(id=get_business_id(request.user.id))
    print(business)

    # If no stripe account id, create one, else retrieve existing
    try:
        stripe.Account.retrieve(business.stripe_id)
    except stripe.error.PermissionError:
        business.stripe_id = None

    if not business.stripe_id:
        account = stripe.Account.create(
            type='standard',
            email=business.email,
        )
        stripe_id = business.stripe_id = account.id
        business.save()
    else:
        stripe_id = business.stripe_id


    account_link = {
        **stripe.AccountLink.create(
            account=stripe_id,
            refresh_url=data['refresh_url'],
            return_url=data['return_url'],
            type="account_onboarding",
        ),
        **{'stripe_id': stripe_id}
    }

    return Response(status=status.HTTP_200_OK, data=account_link)


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
