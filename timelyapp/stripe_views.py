from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.decorators import authentication_classes, permission_classes
from .serializers import *

from .mail import *
from .utils import *
from decimal import Decimal
import stripe
import datetime

stripe.api_key = settings.STRIPE_SECRET_KEY
timely_rate = Decimal(0.001) #0.1%

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
class StripePayInvoice(APIView):
    serializer_class = PayInvoiceSerializer
    permission_classes = []

    def get(self, request):
        if request.user.is_authenticated:
            pm_dict, pm_list = list_payment_methods(Business.objects.get(pk=request.user.business.id))
        else:
            pm_list = {'No payment methods': 'User is not logged in.'}
        return Response(status=status.HTTP_200_OK, data=pm_list)

    def post(self, request):
        # Extract request data
        data = request.data
        invoice = Invoice.objects.get(pk=request.data['invoice_id'])
        billing_business = Business.objects.get(business_name=invoice.bill_from)
        timely_fee = round(timely_rate * 100 * invoice.invoice_total_price)  # Calculate our fee

        data._mutable = True
        data['currency'] = invoice.currency.lower()

        # Check if other account is onboarded, if not we'll have to handle this somehow (hold money until they onboard?)
        if not stripe.Account.retrieve(billing_business.stripe_act_id).charges_enabled:
            if not billing_business.stripe_act_id:
                content = {'Bad invoice': 'Account for ' + billing_business.business_name +
                                          ' has no stripe account'}
            else:
                content = {'Bad invoice': 'Stripe account ' + billing_business.stripe_act_id +
                                          ' for receivable is not fully onboarded.'}
            return Response(content, status=status.HTTP_404_NOT_FOUND)

        # If user is authenticated, check if correct payer and optionally pull default payment method if none specified
        if request.user.is_authenticated:
            stripe_cus_id = Business.objects.get(pk=request.user.business.id).stripe_cus_id

            try:
                customer = stripe.Customer.retrieve(stripe_cus_id)
            except stripe.error.InvalidRequestError:
                content = {'Bad invoice': 'Not a valid customer ID'}
                return Response(content, status=status.HTTP_404_NOT_FOUND)

            # Check if the current user has authority to pay
            if Business.objects.get(business_name=invoice.bill_to).id != request.user.business.id:
                content = {'Bad invoice': 'You are not authorized to pay this invoice'}
                return Response(content, status=status.HTTP_404_NOT_FOUND)

            # Use default method if not provided
            if 'payment_method' not in data:
                data['payment_method'] = customer.invoice_settings.default_payment_method

        # Fill in the method type once populated
        payment_method = stripe.PaymentMethod.retrieve(data['payment_method'])
        stripe_cus_id = payment_method.customer
        data['payment_method_types'] = [payment_method.type]

        # Clone customer to connected account
        payment_method = stripe.PaymentMethod.create(
            customer=stripe_cus_id,
            payment_method=data['payment_method'],
            stripe_account=billing_business.stripe_act_id,
        )

        invoice_desc = "Invoice: " + invoice.invoice_name + \
                    " from " + Business.objects.get(pk=invoice.bill_from.id).business_name +\
                    " to " + Business.objects.get(pk=invoice.bill_to.id).business_name

        payment_intent = stripe.PaymentIntent.create(
            amount=int(invoice.invoice_total_price * 100),
            currency=data['currency'],
            description=invoice_desc,
            payment_method_types=data['payment_method_types'],
            payment_method=payment_method,
            # customer=this_business.stripe_cus_id,
            stripe_account=billing_business.stripe_act_id,
            confirm=True,
            application_fee_amount=timely_fee,
        )

        # # Confirmation
        # payment_intent = stripe.PaymentIntent.confirm(
        #     payment_intent.id,
        #     payment_method=payment_method,
        # )

        if payment_intent.status == 'succeeded':
            invoice.is_paid = True
            invoice.date_paid = datetime.date.today()
            invoice.save()
            # send_payment_confirmation()

        return Response(status=status.HTTP_200_OK, data=payment_intent)

class StripeAttachPaymentMethod(APIView):
    serializer_class = AttachPaymentMethodSerializer

    def get(self, request):
        pm_dict, pm_list = list_payment_methods(Business.objects.get(pk=request.user.business.id))
        return Response(status=status.HTTP_200_OK, data=pm_list)

    def post(self, request):
        # Get the current business
        business = Business.objects.get(pk=request.user.business.id)

        if not business.stripe_cus_id or business.stripe_cus_id == "":
            content = {"Error": "Missing customer ID. User not yet onboarded?"}
            return Response(content, status=status.HTTP_404_NOT_FOUND)

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

class StripeDefaultPaymentMethod(APIView):
    serializer_class = DefaultPaymentMethodSerializer

    def get(self, request):
        pm_dict, pm_list = list_payment_methods(Business.objects.get(pk=request.user.business.id))
        current_default = {x: pm_dict[x] for x in pm_dict if pm_dict[x]['default']}
        return Response(status=status.HTTP_200_OK, data=current_default)

    def post(self, request):
        # Get the current business
        business = Business.objects.get(pk=request.user.business.id)

        if not business.stripe_cus_id or business.stripe_cus_id == "":
            content = {"Error": "Missing customer ID. User not yet onboarded?"}
            return Response(content, status=status.HTTP_404_NOT_FOUND)

        # Get existing payment methods attached, if any
        pm_dict, pm_list = list_payment_methods(business)

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
        payment_method = stripe.PaymentMethod.retrieve(request.data['default_payment_method'])
        payment_method = stripe.Customer.modify(
            business.stripe_cus_id,
            invoice_settings={'default_payment_method': payment_method.id}
        )

        # Update they payment method list
        pm_dict, pm_list = list_payment_methods(business)
        current_default = {x: pm_dict[x] for x in pm_dict if pm_dict[x]['default']}
        return Response(status=status.HTTP_200_OK, data=current_default)

class StripeOnboard(APIView):
    def get(self, request):
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
