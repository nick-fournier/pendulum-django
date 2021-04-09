# serializers.py

from rest_framework import serializers

from .models import *


class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'

class InvoiceSerializer(serializers.ModelSerializer):
    bill_from = BusinessSerializer(read_only=True)
    bill_to = BusinessSerializer(read_only=True)
    orders = OrderSerializer(many=True, read_only=True)
    class Meta:
        model = Invoice
        fields = ['bill_from',
                  'bill_to',
                  'date_sent',
                  'date_due',
                  'terms',
                  'total_price',
                  'currency',
                  'is_flagged',
                  'is_scheduled',
                  'is_paid',
                  'orders'] #'__all__'

