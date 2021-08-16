from django.shortcuts import redirect
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse_lazy, reverse
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import UpdateModelMixin
from decimal import Decimal
from .serializers import *
from .forms import *
from .permissions import *
from timelyapp.utils import get_business_id
import stripe


stripe.api_key = settings.STRIPE_SECRET_KEY
timely_rate = Decimal(0.001) #0.1%


from django.shortcuts import render
def chart_view(request):
    return render(request, 'chart.html')

#### General Functions ####
def list_payment_methods(business):
    # Get payment methods, if any
    pm_dict = {}
    pm_list = []
    try:
        payment_methods = stripe.PaymentMethod.list(
            customer=business.stripe_cus_id,
            type="card",
        )['data']

        customer = stripe.Customer.retrieve(business.stripe_cus_id)

        for x in payment_methods:
            meta = {
                **{'id': x['id']},
                **{i: x['card'].get(i) for i in ['brand', 'last4', 'exp_month', 'exp_year']},
                **{'default': True if x['id'] == customer.invoice_settings.default_payment_method else False}
             }
            meta = {
                **meta,
                **{"summary": "{brand} ************{last4} exp:{exp_month}/{exp_year}".format(**meta)}
            }
            pm_list.append(meta)

            pm_dict[x['id']] = {
                **{"summary": "{brand} ************{last4} exp:{exp_month}/{exp_year}".format(**meta)},
                **meta,
                **{'default': True if x['id'] == customer.invoice_settings.default_payment_method else False}
            }

    except stripe.error.InvalidRequestError:
        content = {'Bad invoice': 'Not a valid customer ID'}
        return Response(content, status=status.HTTP_404_NOT_FOUND)

    return pm_dict, pm_list


### Stripe views ###
# This function takes invoice ID posted and sends back a payment intent
@api_view(['GET', 'POST'])
def stripe_pay_invoice(request):

    # Get business data for the business paying the charge
    this_business = Business.objects.get(pk=get_business_id(request.user.id))

    # Get payment methods, if any
    pm_dict, pm_list = list_payment_methods(this_business)

    if request.method == 'POST':
        # Check if invoice exists
        try:
            if 'invoice_id' in request.data:
                invoice = Invoice.objects.get(pk=request.data['invoice_id'])
            elif 'invoice_name' in request.data:
                invoice = Invoice.objects.get(invoice_name=request.data['invoice_name'])

            billing_business = Business.objects.get(business_name=invoice.bill_from)
            timely_fee = round(timely_rate * 100 * invoice.invoice_total_price) # Calculate our fee
        except Invoice.DoesNotExist:
            content = {'Bad invoice': 'No matching invoice ID in records'}
            return Response(content, status=status.HTTP_404_NOT_FOUND)

        try:
            customer = stripe.Customer.retrieve(this_business.stripe_cus_id)
        except stripe.error.InvalidRequestError:
            content = {'Bad invoice': 'Not a valid customer ID'}
            return Response(content, status=status.HTTP_404_NOT_FOUND)

        # Extract request data
        data = request.data

        if 'payment_method_types' not in data:
            data['payment_method_types'] = ['card']

        if 'currency' not in data:
            data['currency'] = invoice.currency.lower()

        if 'payment_method' not in data:
            data['payment_method'] = customer.invoice_settings.default_payment_method


        if data['payment_method'] == None:
            content = {'Bad invoice': 'User does not have a default payment method. Specify payment method or set a default.'}
            return Response(content, status=status.HTTP_404_NOT_FOUND)

        # Check if the current user has authority to pay
        if Business.objects.get(business_name=invoice.bill_to).id != get_business_id(request.user.id):
            content = {'Bad invoice': 'You are not authorized to pay this invoice'}
            return Response(content, status=status.HTTP_404_NOT_FOUND)

        # Check if other account is onboarded, if not we'll have to handle this somehow (hold money until they onboard?)
        if not stripe.Account.retrieve(billing_business.stripe_act_id).charges_enabled:
            if not billing_business.stripe_act_id:
                content = {'Bad invoice': 'Account for ' + billing_business.business_name +
                                          ' has no stripe account'}
            else:
                content = {'Bad invoice': 'Stripe account ' + billing_business.stripe_act_id +
                                          ' for receivable is not fully onboarded.'}

            return Response(content, status=status.HTTP_404_NOT_FOUND)

        cust_desc = "Invoice: " + invoice.invoice_name + \
                    " from " + Business.objects.get(pk=invoice.bill_to.id).business_name

        # Clone customer to connected account
        payment_method = stripe.PaymentMethod.create(
            customer=this_business.stripe_cus_id,
            payment_method=data['payment_method'],
            stripe_account=billing_business.stripe_act_id,
        )

        payment_intent = stripe.PaymentIntent.create(
            amount=int(invoice.invoice_total_price*100),
            currency=data['currency'],
            description=cust_desc,
            payment_method_types=data['payment_method_types'],
            payment_method=payment_method,
            #customer=this_business.stripe_cus_id,
            stripe_account=billing_business.stripe_act_id,
            confirm=True,
            application_fee_amount=timely_fee,
        )

        # # Confirmation
        # payment_intent = stripe.PaymentIntent.confirm(
        #     payment_intent.id,
        #     payment_method=payment_method,
        # )

        return Response(status=status.HTTP_200_OK, data=payment_intent)

    return Response(status=status.HTTP_200_OK, data=pm_list)

@api_view(['GET', 'POST'])
def attach_payment_methods(request):
    # Get the current business
    business = Business.objects.get(pk=get_business_id(request.user.id))

    if not business.stripe_cus_id or business.stripe_cus_id == "":
        content = {"Error": "Missing customer ID. User not yet onboarded?"}
        return Response(content, status=status.HTTP_404_NOT_FOUND)

    # Get existing payment methods attached, if any
    pm_dict, pm_list = list_payment_methods(business)

    if request.method == 'POST':
        if 'attach_payment_method' in request.data:
            # Attach method to customer
            try:
                payment_method = stripe.PaymentMethod.attach(
                    request.data['attach_payment_method'],
                    customer=business.stripe_cus_id
                )
            except stripe.error.InvalidRequestError:
                content = {"Error": "No such payment method"}
                return Response(content, status=status.HTTP_404_NOT_FOUND)

            # Update payment method list
            pm_dict, pm_list = list_payment_methods(business)
            return Response(status=status.HTTP_200_OK, data=pm_list)

    return Response(status=status.HTTP_200_OK, data=pm_list)

# Set new default payment method
@api_view(['GET', 'POST'])
def default_payment_methods(request):
    # Get the current business
    business = Business.objects.get(pk=get_business_id(request.user.id))

    if not business.stripe_cus_id or business.stripe_cus_id == "":
        content = {"Error": "Missing customer ID. User not yet onboarded?"}
        return Response(content, status=status.HTTP_404_NOT_FOUND)

    # Get existing payment methods attached, if any
    pm_dict, pm_list = list_payment_methods(business)
    current_default = {x: pm_dict[x] for x in pm_dict if pm_dict[x]['default']}

    if request.method == 'POST':
        if 'default_payment_method' in request.data:
            # Attach method to customer if not already
            if request.data['default_payment_method'] not in pm_dict.keys():
                # Attach method to customer
                try:
                    payment_method = stripe.PaymentMethod.attach(
                        request.data['default_payment_method'],
                        customer=business.stripe_cus_id
                    )
                except stripe.error.InvalidRequestError:
                    content = {"Error": "No such payment method"}
                    return Response(content, status=status.HTTP_404_NOT_FOUND)

            # Set default on stripe and in database
            payment_method = stripe.Customer.modify(
                business.stripe_cus_id,
                invoice_settings={'default_payment_method': payment_method.id}
            )

            # Update they payment method list
            pm_dict, pm_list = list_payment_methods(business)
            current_default = {x: pm_dict[x] for x in pm_dict if pm_dict[x]['default']}
            return Response(status=status.HTTP_200_OK, data=current_default)

    return Response(status=status.HTTP_200_OK, data=current_default)

#This function retrieves currently logged in user and returns the stripe AccountLink, no POST data is required
@api_view(['GET'])
def stripe_onboard(request):
    # sub-func to create new stripe account and add to db
    def create_stripe_account():
        account = stripe.Account.create(
            type='standard',
            email=business.email,
        )
        business.stripe_act_id = account.id
        business.save()
        return account

    def create_stripe_customer():
        customer = stripe.Customer.create(
            description=business.business_name,
            email=business.email
        )
        business.stripe_cus_id = customer.stripe_id
        business.save()
        return customer

    # Parse any data passed
    data = request.data
    if 'refresh_url' not in data:
        data['refresh_url'] = 'https://www.timelypay.app/invoices' # request.build_absolute_uri('/invoices/')
    if 'return_url' not in data:
        data['return_url'] = 'https://www.timelypay.app/invoices' # request.build_absolute_uri('/invoices/')

    # Query current business
    business = Business.objects.get(id=get_business_id(request.user.id))

    # Check if stripe_act_id in database is not null
    if business.stripe_act_id:
        # Check if database stripe_act_id is on stripe API
        try:
            stripe.Account.retrieve(business.stripe_act_id)['id']
        # If not, create a new account
        except stripe.error.PermissionError:
            create_stripe_account()
    else:
        create_stripe_account()

    # Check if stripe_cus_id in database is not null
    if business.stripe_cus_id:
        # Check if database stripe_act_id is on stripe API
        try:
            stripe.Customer.retrieve(business.stripe_cus_id)['id']
        # If not, create a new account
        except stripe.error.PermissionError:
            create_stripe_customer()
    else:
        create_stripe_customer()

    account_link = {
        **stripe.AccountLink.create(
            account=business.stripe_act_id,
            refresh_url=data['refresh_url'],
            return_url=data['return_url'],
            type='account_onboarding',
        ),
        **{'stripe_act_id': business.stripe_act_id},
        **{'stripe_cus_id': business.stripe_cus_id},
    }

    return Response(status=status.HTTP_200_OK, data=account_link)

#### Timely Views ####
# Create your views here.
def redirect_view(request):
    response = redirect('/api/')
    return response

class BusinessInfo(viewsets.ModelViewSet):
    serializer_class = BusinessInfoSerializer

    def get_queryset(self):
        queryset = self.queryset

        try:
            business = Business.objects.get(id=get_business_id(self.request.user.id))
            queryset = queryset.filter(owner__id=business.id)
        except Business.DoesNotExist:
            queryset = []

        # Checking if data is current
        # account_info = stripe.Account.retrieve(queryset.get().stripe_act_id)

        return queryset


class UserInfo(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    #permission_classes = (UserPermissions, )

    def get_queryset(self):
        return CustomUser.objects.filter(pk=self.request.user.id)

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


# Django REST framework endpoints
class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FullInvoiceSerializer

    def get_queryset(self):
        business_id = get_business_id(self.request.user.id)
        queryset = Invoice.objects.filter(Q(bill_from__id=business_id) | Q(bill_to__id=business_id)).order_by('id')
        return queryset

class NewInvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = NewInvoiceSerializer

    def get_queryset(self):
        business_id = get_business_id(self.request.user.id)
        queryset = Invoice.objects.filter(bill_from__id=business_id)
        return queryset


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
        query_set = Order.objects.filter(pk__in=item_list)
        return query_set


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

class NewsletterViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = NewsletterSerializer
    queryset = Newsletter.objects.none()
    success_url = reverse_lazy('home')
