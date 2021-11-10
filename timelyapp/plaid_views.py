from rest_framework import viewsets, status, mixins
from rest_framework.response import Response
from .plaid_serializers import *

import plaid
from plaid.api import plaid_api

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
        bank_account_token = stripe_response['stripe_bank_account_token']

        response = {'request_id': stripe_response.request_id,
                    'stripe_bank_account_token': stripe_response.stripe_bank_account_token}
        # # Attach method to customer
        # try:
        #     payment_method = stripe.PaymentMethod.attach(
        #         stripe_response['stripe_bank_account_token'],
        #         customer=request.user.business.stripe_cus_id
        #
        #     )
        # except stripe.error.InvalidRequestError:
        #     content = {"Error": "Failed to attach payment method to Stripe"}
        #     return Response(content, status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_200_OK, data=response)
