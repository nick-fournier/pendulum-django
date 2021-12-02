from rest_framework import serializers
from .mail import *

# PAY INVOICE SERIALIZER
class PayInvoiceObjectSerializer(serializers.ModelSerializer):
    payment_method = serializers.CharField(required=True)
    type = serializers.CharField(required=True)
    stripe_cus_id = serializers.CharField(required=False)

    class Meta:
        model = Invoice
        fields = ['payment_method', 'type', 'stripe_cus_id']

class PayInvoiceSerializer(serializers.ModelSerializer):
    invoice_id = serializers.CharField(required=True)
    payment_method = serializers.CharField(required=True)
    type = serializers.CharField(required=True)
    stripe_cus_id = serializers.CharField(required=False)

    class Meta:
        model = Invoice
        fields = ['invoice_id', 'payment_method', 'type', 'stripe_cus_id']

class ConfirmPayInvoiceSerializer(serializers.ModelSerializer):
    invoice_id = serializers.CharField(required=True)
    payment_intent = serializers.CharField(required=True)
    payment_method = serializers.CharField(required=True)

    class Meta:
        model = Invoice
        fields = ['invoice_id', 'payment_intent', 'payment_method']


# PAYMENT METHOD SERIALIZER
class PaymentMethodSerializer(serializers.ModelSerializer):
    payment_method = serializers.CharField(required=True)
    action = serializers.CharField(required=True)

    class Meta:
        model = Business
        fields = ['payment_method', 'action']

class PlaidLinkTokenSerializer(serializers.ModelSerializer):
    public_token = serializers.CharField(required=True)
    plaid_account_id = serializers.CharField(required=True)
    oon_name = serializers.CharField(required=False)
    oon_email = serializers.CharField(required=False)

    class Meta:
        model = Business
        fields = ['public_token', 'plaid_account_id', 'oon_name', 'oon_email']
