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
    type = serializers.CharField(required=True)

    class Meta:
        model = Invoice
        fields = ['invoice_id', 'payment_method', 'type']

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

# # ATTACH PAYMENT METHOD SERIALIZER
# class AttachPaymentMethodSerializer(serializers.ModelSerializer):
#     attach_payment_method = serializers.CharField(required=True)
#
#     class Meta:
#         model = Business
#         fields = ['attach_payment_method']
#
# # DEFAULT PAYMENT METHOD SERIALIZER
# class DefaultPaymentMethodSerializer(serializers.ModelSerializer):
#     default_payment_method = serializers.CharField(required=True)
#
#     class Meta:
#         model = Business
#         fields = ['default_payment_method']

class PlaidLinkTokenSerializer(serializers.ModelSerializer):
    public_token = serializers.CharField(required=True)
    plaid_account_id = serializers.CharField(required=True)

    class Meta:
        model = Business
        fields = ['public_token', 'plaid_account_id']
