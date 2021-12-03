from rest_framework import viewsets, status, mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import *
from .stripe_serializers import *

from .mail import *
from .utils import *
from decimal import Decimal

import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode

import stripe
import datetime

#### PLAID API
# Available environments are
# 'Production'
# 'Development'
# 'Sandbox'
plaid_configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        'clientId': settings.PLAID_CLIENT_ID,
        'secret': settings.PLAID_SECRET,
    }
)
plaid_api_client = plaid.ApiClient(plaid_configuration)
plaid_client = plaid_api.PlaidApi(plaid_api_client)

### STRIPE API
stripe.api_key = settings.STRIPE_SECRET_KEY
timely_rate = Decimal(0.000)

#### General Functions ####
def list_payment_methods(request, types = None):
    # Get payment methods, if any
    pm_dict = {}
    pm_list = []

    if types is None:
        types = ['ach', 'card']
    elif isinstance(types, list):
        types = [x.lower() for x in types]
    else:
        types = [types.lower()]

    try:
        customer = stripe.Customer.retrieve(request.user.business.stripe_cus_id)
        payment_methods = stripe.Customer.list_payment_methods(
            request.user.business.stripe_cus_id,
            type="card",
        )

        if 'card' in types:
            for x in payment_methods:
                meta = {
                    **{'id': x['id'], 'type': 'card'},
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

        if 'ach' in types:
            # Add bank sources
            bank_sources = stripe.Customer.list_sources(
                request.user.business.stripe_cus_id,
                object='bank_account',
                limit=10
            )['data']

            for x in bank_sources:
                pm_dict[x['id']] = {
                    "id": x['id'],
                    "type": 'ach',
                    "brand": x['bank_name'],
                    "last4": x['last4'],
                    "exp_month": None,
                    "exp_year": None,
                    "default": None,
                    "summary": "{bank_name} ************{last4}".format(**x)
                }
                pm_list.append(pm_dict[x['id']])

    except stripe.error.InvalidRequestError:
        content = {'Bad invoice': 'Not a valid customer ID'}
        return Response(content, status=status.HTTP_404_NOT_FOUND)

    return pm_dict, pm_list


# sub-func to create new stripe account and add to db
def create_stripe_account(request):
    account = stripe.Account.create(
        type='standard',
        email=request.business.email,
    )
    business_model = Business.objects.get(id=request.user.business.id)
    business_model.stripe_act_id = account.id
    business_model.save()
    return account

def create_stripe_customer(request):
    customer = stripe.Customer.create(
        description=request.user.business.business_name,
        email=request.user.business.email
    )
    business_model = Business.objects.get(id=request.user.business.id)
    business_model.stripe_cus_id = customer.stripe_id
    business_model.save()
    return customer

### Stripe views ###
class StripeOnboard(mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    def list(self, request):
        # Parse any data passed
        data = request.data
        if 'refresh_url' not in data:
            data['refresh_url'] = 'https://dash.pendulumapp.com/'  # request.build_absolute_uri('/invoices/')
        if 'return_url' not in data:
            data['return_url'] = 'https://dash.pendululapp.com/'  # request.build_absolute_uri('/invoices/')

        # Check if stripe_act_id in database is not null
        if request.user.business.stripe_act_id:
            # Check if database stripe_act_id is on stripe API
            try:
                stripe.Account.retrieve(request.user.business.stripe_act_id)['id']
            # If not, create a new account
            except stripe.error.PermissionError:
                create_stripe_account(request)
        else:
            create_stripe_account(request)

        # Check if stripe_cus_id in database is not null
        if request.user.business.stripe_cus_id:
            # Check if database stripe_act_id is on stripe API
            try:
                stripe.Customer.retrieve(request.user.business.stripe_cus_id)['id']
            # If not, create a new account
            except stripe.error.PermissionError:
                create_stripe_customer(request)
        else:
            create_stripe_customer(request)

        account_link = {
            **stripe.AccountLink.create(
                account=request.user.business.stripe_act_id,
                refresh_url=data['refresh_url'],
                return_url=data['return_url'],
                type='account_onboarding',
            ),
            **{'stripe_act_id': request.user.business.stripe_act_id},
            **{'stripe_cus_id': request.user.business.stripe_cus_id},
        }

        return Response(status=status.HTTP_200_OK, data=account_link)


class StripePaymentMethods(mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           mixins.CreateModelMixin,
                           mixins.UpdateModelMixin,
                           viewsets.GenericViewSet):

    serializer_class = PaymentMethodSerializer
    queryset = Business.objects.all()

    def list(self, request):
        if request.user.is_authenticated:
            pm_dict, pm_list = list_payment_methods(request, types=['ach', 'card'])
        else:
            pm_list = {'No payment methods': 'User is not logged in.'}
        return Response(status=status.HTTP_200_OK, data=pm_list)

    def retrieve(self, request, pk=None):
        if request.user.is_authenticated:
            pm_dict, pm_list = list_payment_methods(request, types=pk)
        else:
            pm_list = {'No payment methods': 'User is not logged in.'}
        return Response(status=status.HTTP_200_OK, data=pm_list)

    def update(self, request, pk=None):
        return self.create(request)

    def partial_update(self, request, pk=None):
        return self.create(request)

    def create(self, request, pk=None):

        pm_dict, pm_list = list_payment_methods(request, types=['ach', 'card'])

        if request.data['action'] is None:
            return Response({'Error': 'No action given.'}, status=status.HTTP_404_NOT_FOUND)

        # Attach function
        def attach(request):
            try:
                return stripe.PaymentMethod.attach(
                    request.data['payment_method'],
                    customer=request.user.business.stripe_cus_id
                )
            except stripe.error.InvalidRequestError:
                content = {"Error": "No such payment method"}
                return Response(content, status=status.HTTP_404_NOT_FOUND)

        # Check if user is onboarded
        if not request.user.business.stripe_cus_id or request.user.business.stripe_cus_id == "":
            content = {"Error": "Missing stripe customer ID. User not yet onboarded?"}
            return Response(content, status=status.HTTP_404_NOT_FOUND)

        if not request.user.business.stripe_act_id or request.user.business.stripe_act_id == "":
            content = {"Error": "Missing stripe account ID. User not yet onboarded?"}
            return Response(content, status=status.HTTP_404_NOT_FOUND)

        # Perform the action
        if request.data['action'] == 'attach':
            # Attach method to customer
            payment_method = attach(request)

            return Response(status=status.HTTP_200_OK,
                            data={'Success': 'Attached payment method: ' + payment_method.id})


        if request.data['action'] == 'default':
            if pm_dict[request.data['payment_method']]['type'] == 'ach':
                return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': 'ach cannot be set as default.'})

            # Attach method to customer if not already
            payment_method = attach(request)

            # Set default on stripe and in database
            #payment_method = stripe.PaymentMethod.retrieve(request.data['payment_method'])
            payment_method = stripe.PaymentMethod.retrieve(payment_method.id)
            payment_method = stripe.Customer.modify(
                request.user.business.stripe_cus_id,
                invoice_settings={'default_payment_method': payment_method.id}
            )

            # Update the payment method list
            pm_dict, pm_list = list_payment_methods(request)

            return Response(status=status.HTTP_200_OK,
                            data={'Success': 'Set default payment method: ' + payment_method.id})

        if request.data['action'] == 'detach':

            if request.data['payment_method'] not in pm_dict.keys():
                return Response({'Error': 'Payment method not found, may already be detached.'}, status=status.HTTP_404_NOT_FOUND)

            if pm_dict[request.data['payment_method']]['type'] == 'card':
                stripe.PaymentMethod.detach(
                    request.data['payment_method']
                )

            if pm_dict[request.data['payment_method']]['type'] == 'ach':
                stripe.Customer.delete_source(
                    request.user.business.stripe_cus_id,
                    request.data['payment_method']
                )

            return Response(status=status.HTTP_200_OK,
                            data={'success': 'detached payment method: ' + request.data['payment_method']})

class StripePayInvoice(mixins.CreateModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       viewsets.GenericViewSet):
    # This exposes the endpoint
    permission_classes = []
    queryset = Invoice.objects.all()

    def get_serializer_class(self):
        if self.action == 'update':
            return PayInvoiceObjectSerializer
        return PayInvoiceSerializer

    def list(self, request):
        if request.user.is_authenticated:
            pm_dict, pm_list = list_payment_methods(request)
            return Response(status=status.HTTP_200_OK, data=pm_list)
        else:
            return Response(status=status.HTTP_200_OK,
                            data={'Not logged in': 'No payment methods to list'})

    def retrieve(self, request, pk=None):
        invoice = Invoice.objects.filter(pk=pk)
        if invoice.exists():
            serializer = InvoiceSerializer(invoice, many=True)
            return Response(serializer.data)
        else:
            return Response({"No invoice matching this request"}, status=status.HTTP_404_NOT_FOUND)

    def create(self, request, pk=None):
        return self.pay_invoice(request, pk=None)

    def update(self, request, pk=None):
        if pk != 'confirm':
            return self.pay_invoice(request, pk)

    def pay_invoice(self, request, pk=None):
        # Extract request
        data = request.data.copy()

        invoice = Invoice.objects.get(pk=pk) if pk else Invoice.objects.get(pk=request.data['invoice_id'])
        billing_business = Business.objects.get(business_name=invoice.bill_from)
        paying_business = Business.objects.get(business_name=invoice.bill_to)
        timely_fee = round(timely_rate * 100 * invoice.invoice_total_price)  # Calculate our fee
        data['currency'] = invoice.currency.lower()

        # Check if other account is onboarded, if not we'll have to handle this somehow (hold money until they onboard?)
        if not stripe.Account.retrieve(billing_business.stripe_act_id).charges_enabled:
            content = {'Account error': 'Account for '
                                        + billing_business.business_name +
                                        'is not fully onboarded and cannot receive payments yet.'}
            return Response(content, status=status.HTTP_404_NOT_FOUND)

        # If user is authenticated, check if correct payer
        if request.user.is_authenticated:
            data['receipt_email'] = request.user.email
            # Double check if account has a stripe customer created. If not create it.
            try:
                customer = stripe.Customer.retrieve(request.user.business.stripe_cus_id)
            except stripe.error.InvalidRequestError:
                customer = create_stripe_customer(request)

            # Check if the current user has authority to pay
            if paying_business.id != request.user.business.id:
                content = {'Bad invoice': 'You are not the payer for this invoice!'}
                return Response(content, status=status.HTTP_404_NOT_FOUND)

        # Description
        invoice_desc = "Invoice: " + invoice.invoice_name + \
                       " from " + billing_business.business_name + \
                       " to " + paying_business.business_name
        # invoice_desc = "Invoice: " + invoice.invoice_name + \
        #                " from " + Business.objects.get(pk=invoice.bill_from.id).business_name + \
        #                " to " + Business.objects.get(pk=invoice.bill_to.id).business_name

        # Use default method if not provided
        if 'payment_method' not in data:
            return Response({'Error': 'No payment method provided.'}, status=status.HTTP_404_NOT_FOUND)
        if 'card' in data['type']:
            try:
                # 1) Retrieve existing payment method
                payment_method = stripe.PaymentMethod.retrieve(data['payment_method'])
                data['payment_method_types'] = [payment_method.type]

                # get receipt email either from payment method or invoice
                if not request.user.is_authenticated:
                    if not payment_method.billing_details.email:
                        data['receipt_email'] = payment_method.billing_details.email
                    else:
                        data['receipt_email'] = paying_business.business_email

                # 2) Clone customer to connected account
                payment_method = stripe.PaymentMethod.create(
                    customer=payment_method.customer,
                    payment_method=payment_method,
                    stripe_account=billing_business.stripe_act_id,
                )

                # 3) Create a payment intent between paying customer and receiving account
                payment = stripe.PaymentIntent.create(
                    amount=int(invoice.invoice_total_price * 100),
                    currency=data['currency'],
                    description=invoice_desc,
                    payment_method_types=data['payment_method_types'],
                    payment_method=payment_method,
                    # customer=payment_method.customer,
                    stripe_account=billing_business.stripe_act_id,
                    application_fee_amount=timely_fee,
                    confirm=True,
                )

            except stripe.error.InvalidRequestError:
                return Response({'Error': 'Card method not found.'}, status=status.HTTP_404_NOT_FOUND)

        if 'ach' in data['type']:
            # Get stripe customer data for ACH, not needed for CARD method
            if not request.user.is_authenticated:
                # Check if it got passed on backend, otherwise pass from endpoint
                # if request.user.stripe_customer:
                #     data['stripe_cus_id'] = request.user.stripe_customer.id

                if not data['stripe_cus_id']:
                    content = {'Error': 'Missing stripe customer id for ach payment!'},
                    return Response(content, status=status.HTTP_404_NOT_FOUND)

                # Retrieve email created from ach link token
                data['receipt_email'] = stripe.Customer.retrieve(data['stripe_cus_id']).email

            try:
                # 1) Retrieve bank account id
                payment_source = stripe.Customer.retrieve_source(
                    data['stripe_cus_id'],
                    data['payment_method']
                )

                # 2) Create a payment method token between the paying customer and receiving account
                payment_token = stripe.Token.create(
                    bank_account=payment_source,
                    customer=data['stripe_cus_id'],
                    stripe_account=billing_business.stripe_act_id,
                )

                # 3) Clone customer to connected account
                customer = stripe.Customer.create(
                    source=payment_token.id,
                    stripe_account=billing_business.stripe_act_id,
                )

                # 3) Create a payment intent between paying customer and receiving account
                payment = stripe.PaymentIntent.create(
                    amount=int(invoice.invoice_total_price * 100),
                    currency=data['currency'],
                    description=invoice_desc,
                    payment_method_types=['ach_debit'],
                    source=customer.default_source,
                    #payment_method=payment_source.id,
                    customer=customer.id,
                    stripe_account=billing_business.stripe_act_id,
                    application_fee_amount=timely_fee,
                    confirm=True,
                )
            except stripe.error.InvalidRequestError:
                return Response({'Error': 'ACH source not found, is this a card?'}, status=status.HTTP_404_NOT_FOUND)

        if payment.status == 'succeeded':
            invoice.is_paid = True
            invoice.date_paid = datetime.date.today()
            invoice.save()
            send_notification(invoice_id=invoice.id, notif_type='confirm', cc=data['receipt_email'])

        return Response(status=status.HTTP_200_OK, data=payment)

class StripeConfirmPayInvoice(mixins.CreateModelMixin,
                              viewsets.GenericViewSet):

    # # This exposes the endpoint
    permission_classes = []
    # This creates the input form
    serializer_class = ConfirmPayInvoiceSerializer
    queryset = Invoice.objects.all()

    def create(self, request):

        invoice = Invoice.objects.get(pk=request.data['invoice_id'])

        # Confirmation
        payment_intent = stripe.PaymentIntent.confirm(
            request.data['payment_intent'],
            payment_method=request.data['payment_method'],
        )

        if payment_intent.status == 'succeeded':
            invoice.is_paid = True
            invoice.date_paid = datetime.date.today()
            invoice.save()
            send_notification(invoice_id=invoice.id, notif_type='confirm')


### Plaid Views ###
# Creates ACH payment method
class PlaidLinkToken(mixins.ListModelMixin,
                     mixins.CreateModelMixin,
                     viewsets.GenericViewSet):

    serializer_class = PlaidLinkTokenSerializer
    # This exposes the endpoint
    permission_classes = []

    def list(self, request):
        if request.user.is_authenticated:
            client_user_id = request.user.business.stripe_cus_id
        else:
            client_user_id = 'out of network customer'

        # create link token
        plaid_request = LinkTokenCreateRequest(
            user=LinkTokenCreateRequestUser(client_user_id=client_user_id),
            products=[Products("auth")],
            client_name="Pendulum App",
            country_codes=[CountryCode('US')],
            language='en',
            webhook='https://dash.pendulumapp.com/invoices',
        )
        response = plaid_client.link_token_create(plaid_request)
        link_token = response['link_token']
        return Response(status=status.HTTP_200_OK, data=link_token)

    def create(self, request):

        exchange_request = plaid.api.plaid_api.ItemPublicTokenExchangeRequest(public_token=request.data['public_token'])
        exchange_token_response = plaid_client.item_public_token_exchange(exchange_request)
        access_token = exchange_token_response['access_token']

        plaid_request = plaid.api.plaid_api.ProcessorStripeBankAccountTokenCreateRequest(
            access_token=access_token,
            account_id=request.data['plaid_account_id']
        )
        stripe_response = plaid_client.processor_stripe_bank_account_token_create(plaid_request)

        # Check if OON user or not
        if request.user.is_authenticated:
            try:
                customer = stripe.Customer.retrieve(request.user.business.stripe_cus_id)
            except stripe.error.InvalidRequestError:
                customer = create_stripe_customer(request)

        else:
            # Checking if email valid
            regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            if not (re.fullmatch(regex, request.data['oon_email'])):
                return Response({'Error': 'Email appears invalid.'}, status=status.HTTP_404_NOT_FOUND)

            if not request.data['oon_name']:
                return Response({'Error': 'Name field is empty.'}, status=status.HTTP_404_NOT_FOUND)

            # Check if customer already exists for this email, otherwise create one
            if stripe.Customer.list(email=request.data['oon_email']).data:
                customer = stripe.Customer.list(email=request.data['oon_email']).data[0]
            else:
                customer = stripe.Customer.create(
                    name=request.data['oon_name'],
                    email=request.data['oon_email'],
                    description='Out of network customer.'
                )
            # request.user.stripe_customer = customer

        # Attach new method to customer
        try:
            bank_account = stripe.Customer.create_source(
                # request.user.business.stripe_cus_id,
                customer.stripe_id,
                source=stripe_response.stripe_bank_account_token,
            )
            error_status = 'successfully attached new bank source.'
        except stripe.error.InvalidRequestError:
            # Try retrieving any existing bank
            try:
                bank_account = stripe.Customer.retrieve_source(
                    customer.stripe_id,
                    stripe_response.stripe_bank_account_token,
                )
                error_status = 'could not attach new bank source, using existing.'

            except stripe.error.InvalidRequestError:
                content = {"Error": "Failed to find or attach ach source to Stripe account."}
                return Response(content, status=status.HTTP_404_NOT_FOUND)

        response = {'request_id': stripe_response.request_id,
                    'stripe_bank_account_token': stripe_response.stripe_bank_account_token,
                    'payment_method': bank_account.id,
                    'stripe_cus_id': customer.id,
                    'error_status': error_status}

        return Response(status=status.HTTP_200_OK, data=response)
