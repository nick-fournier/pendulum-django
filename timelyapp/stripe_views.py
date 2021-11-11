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
timely_rate = Decimal(0.001) #0.1%

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

### Stripe views ###
class StripeOnboard(mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    def list(self, request):
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
            data['refresh_url'] = 'https://dash.pendulumapp.com/'  # request.build_absolute_uri('/invoices/')
        if 'return_url' not in data:
            data['return_url'] = 'https://dash.pendululapp.com/'  # request.build_absolute_uri('/invoices/')

        # Query current business
        business = Business.objects.get(id=request.user.business.id)

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

    def create(self, request, pk=None):

        pm_dict, pm_list = list_payment_methods(request, types=['ach', 'card'])

        # Attach function
        def attach(request):
            try:
                stripe.PaymentMethod.attach(
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
            attach(request)

        if request.data['action'] == 'default':
            if pm_dict[request.data['payment_method']]['type'] == 'ach':
                return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': 'ach cannot be set as default.'})

            # Attach method to customer if not already
            attach(request)

            # Set default on stripe and in database
            payment_method = stripe.PaymentMethod.retrieve(request.data['payment_method'])
            payment_method = stripe.Customer.modify(
                request.user.business.stripe_cus_id,
                invoice_settings={'default_payment_method': payment_method.id}
            )

            # Update the payment method list
            pm_dict, pm_list = list_payment_methods(request)
            return Response(status=status.HTTP_200_OK, data=pm_list)

        if request.data['action'] == 'detach':

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


# class StripeAttachPaymentMethod(mixins.ListModelMixin,
#                                 mixins.CreateModelMixin,
#                                 viewsets.GenericViewSet):
#
#     serializer_class = AttachPaymentMethodSerializer
#     queryset = Business.objects.all()
#
#     def list(self, request):
#         pm_dict, pm_list = list_payment_methods(request)
#         return Response(status=status.HTTP_200_OK, data=pm_list)
#
#     def create(self, request):
#         # Get the current business
#         business = Business.objects.get(pk=request.user.business.id)
#
#         if not business.stripe_cus_id or business.stripe_cus_id == "":
#             content = {"Error": "Missing customer ID. User not yet onboarded?"}
#             return Response(content, status=status.HTTP_404_NOT_FOUND)
#
#         # Attach method to customer
#         try:
#             payment_method = stripe.PaymentMethod.attach(
#                 request.data['attach_payment_method'],
#                 customer=business.stripe_cus_id
#             )
#         except stripe.error.InvalidRequestError:
#             content = {"Error": "No such payment method"}
#             return Response(content, status=status.HTTP_404_NOT_FOUND)
#
#         # Update payment method list
#         pm_dict, pm_list = list_payment_methods(request)
#
#         return Response(status=status.HTTP_200_OK, data=pm_list)
#
# class StripeDefaultPaymentMethod(mixins.CreateModelMixin,
#                                  mixins.ListModelMixin,
#                                  viewsets.GenericViewSet):
#
#     serializer_class = DefaultPaymentMethodSerializer
#     queryset = Business.objects.all()
#
#     def list(self, request):
#         if request.user.is_authenticated:
#             pm_dict, pm_list = list_payment_methods(Business.objects.get(pk=request.user.business.id))
#             current_default = {x: pm_dict[x] for x in pm_dict if pm_dict[x]['default']}
#
#             if not current_default:
#                 current_default = {'No default payment method'}
#         else:
#             current_default = {'No payment methods': 'User is not logged in.'}
#         return Response(status=status.HTTP_200_OK, data=current_default)
#
#     def create(self, request):
#         # Get the current business
#         business = Business.objects.get(pk=request.user.business.id)
#
#         if not business.stripe_cus_id or business.stripe_cus_id == "":
#             content = {"Error": "Missing customer ID. User not yet onboarded?"}
#             return Response(content, status=status.HTTP_404_NOT_FOUND)
#
#         # Get existing payment methods attached, if any
#         pm_dict, pm_list = list_payment_methods(business)
#
#         # Attach method to customer if not already
#         if request.data['default_payment_method'] not in pm_dict.keys():
#             # Attach method to customer
#             try:
#                 payment_method = stripe.PaymentMethod.attach(
#                     request.data['default_payment_method'],
#                     customer=business.stripe_cus_id
#                 )
#             except stripe.error.InvalidRequestError:
#                 content = {"Error": "No such payment method"}
#                 return Response(content, status=status.HTTP_404_NOT_FOUND)
#
#         # Set default on stripe and in database
#         payment_method = stripe.PaymentMethod.retrieve(request.data['default_payment_method'])
#         payment_method = stripe.Customer.modify(
#             business.stripe_cus_id,
#             invoice_settings={'default_payment_method': payment_method.id}
#         )
#
#         # Update they payment method list
#         pm_dict, pm_list = list_payment_methods(business)
#         current_default = {x: pm_dict[x] for x in pm_dict if pm_dict[x]['default']}
#         return Response(status=status.HTTP_200_OK, data=current_default)

class StripePayInvoice(mixins.CreateModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       viewsets.GenericViewSet):
    # # This exposes the endpoint
    permission_classes = []
    # This creates the input form
    # serializer_class = PayInvoiceObjectSerializer
    queryset = Invoice.objects.all()

    def get_serializer_class(self):
        if self.action == 'update':
            return PayInvoiceObjectSerializer
        return PayInvoiceSerializer

    def list(self, request):
        if request.user.is_authenticated:
            pm_dict, pm_list = list_payment_methods(request)
        else:
            pm_list = {'No payment methods': 'User is not logged in.'}
        return Response(status=status.HTTP_200_OK, data=pm_list)

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
        if pk == 'confirm':
            pass
        else:
            return self.pay_invoice(request, pk)

    def pay_invoice(self, request, pk=None):
        # Extract request
        data = request.data.copy()

        invoice = Invoice.objects.get(pk=pk) if pk else Invoice.objects.get(pk=request.data['invoice_id'])
        billing_business = Business.objects.get(business_name=invoice.bill_from)
        timely_fee = round(timely_rate * 100 * invoice.invoice_total_price)  # Calculate our fee
        data['currency'] = invoice.currency.lower()

        #if 'pm' in data['payment_method'] and data['type'] != 'ach':

        # Check if other account is onboarded, if not we'll have to handle this somehow (hold money until they onboard?)
        if not stripe.Account.retrieve(billing_business.stripe_act_id).charges_enabled:
            content = {'Account error': 'Account for '
                                        + billing_business.business_name +
                                        'is not fully onboarded and cannot receive payments yet.'}
            return Response(content, status=status.HTTP_404_NOT_FOUND)

        # If user is authenticated, check if correct payer and optionally pull default payment method if none specified
        if request.user.is_authenticated:
            try:
                customer = stripe.Customer.retrieve(request.user.business.stripe_cus_id)
            except stripe.error.InvalidRequestError:
                content = {'Stripe error': 'User has bad customer id. Possibly not onboarded'}
                return Response(content, status=status.HTTP_404_NOT_FOUND)

            # Check if the current user has authority to pay
            if Business.objects.get(business_name=invoice.bill_to).id != request.user.business.id:
                content = {'Bad invoice': 'You are not the payer for this invoice!'}
                return Response(content, status=status.HTTP_404_NOT_FOUND)

        # Out of network users pay here
        else:
            #TODO
            return Response({'error': 'Have not implemented out of network charges yet!!!'}, status=status.HTTP_404_NOT_FOUND)


        # Description
        invoice_desc = "Invoice: " + invoice.invoice_name + \
                       " from " + Business.objects.get(pk=invoice.bill_from.id).business_name + \
                       " to " + Business.objects.get(pk=invoice.bill_to.id).business_name

        # Use default method if not provided
        if 'payment_method' not in data:
            data['payment_method'] = customer.invoice_settings.default_payment_method

        if 'card' in data['type']:
            try:
                # 1) Retrieve existing payment method
                payment_method = stripe.PaymentMethod.retrieve(data['payment_method'])
                data['payment_method_types'] = [payment_method.type]

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
                return Response({'Error': 'ACH source not found, is this a card?'}, status=status.HTTP_404_NOT_FOUND)

        if 'ach' in data['type']:
            try:
                # 1) Retrieve bank account id
                payment_source = stripe.Customer.retrieve_source(
                    request.user.business.stripe_cus_id,
                    data['payment_method']
                )
                data['payment_method_types'] = [payment_source.object]

                # 2) Create a payment method token between the paying customer and receiving account
                payment_token = stripe.Token.create(
                    bank_account=payment_source,
                    customer=request.user.business.stripe_cus_id,
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
            send_notification(invoice_id=invoice.id, notif_type='confirm')

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
class PlaidLinkToken(mixins.ListModelMixin,
                     mixins.CreateModelMixin,
                     viewsets.GenericViewSet):

    serializer_class = PlaidLinkTokenSerializer

    def list(self, request):
        # create link token
        response = plaid_client.link_token_create({
            'user': {
                'client_user_id': request.user.business.id,
            },
            'products': ["auth"],
            'client_name': "Pendulum App",
            'country_codes': ['US'],
            'language': 'en',
            'webhook': 'https://dash.pendulumapp.com/invoices',
        })
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

        response = {'request_id': stripe_response.request_id,
                    'stripe_bank_account_token': stripe_response.stripe_bank_account_token}

        # Attach method to customer
        try:
            stripe.Customer.create_source(
                request.user.business.stripe_cus_id,
                source=stripe_response.stripe_bank_account_token,
            )
            # payment_method = stripe.PaymentMethod.attach(
            #     stripe_response['stripe_bank_account_token'],
            #     customer=request.user.business.stripe_cus_id
            #
            # )
        except stripe.error.InvalidRequestError:
            content = {"Error": "Failed to attach payment method to Stripe. May already be attached."}
            return Response(content, status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_200_OK, data=response)
