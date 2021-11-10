from rest_framework import serializers
from .mail import *

# PAY INVOICE SERIALIZER
class PayInvoiceObjectSerializer(serializers.ModelSerializer):
    payment_method = serializers.CharField(required=True)

    class Meta:
        model = Invoice
        fields = ['payment_method']

class PayInvoiceSerializer(serializers.ModelSerializer):
    invoice_id = serializers.CharField(required=True)
    payment_method = serializers.CharField(required=True)

    class Meta:
        model = Invoice
        fields = ['invoice_id', 'payment_method']

# ATTACH PAYMENT METHOD SERIALIZER
class AttachPaymentMethodSerializer(serializers.ModelSerializer):
    attach_payment_method = serializers.CharField(required=True)

    class Meta:
        model = Business
        fields = ['attach_payment_method']

# DEFAULT PAYMENT METHOD SERIALIZER
class DefaultPaymentMethodSerializer(serializers.ModelSerializer):
    default_payment_method = serializers.CharField(required=True)

    class Meta:
        model = Business
        fields = ['default_payment_method']

class PlaidLinkTokenSerializer(serializers.ModelSerializer):
    public_token = serializers.CharField(required=True)
    plaid_account_id = serializers.CharField(required=True)

    class Meta:
        model = Business
        fields = ['public_token', 'plaid_account_id']
