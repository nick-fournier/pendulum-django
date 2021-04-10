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
    items = OrderSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = '__all__'


class PayablesSerializer(serializers.ModelSerializer):
    invoice_id = serializers.IntegerField(source='id')
    items = OrderSerializer(many=True, read_only=True)
    address = serializers.SerializerMethodField()
    business_name = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ('invoice_id',
                  'bill_to',
                  'bill_from',
                  'business_name',
                  'address',
                  'date_sent',
                  'date_due',
                  'terms',
                  'total_price',
                  'currency',
                  'is_flagged',
                  'is_scheduled',
                  'is_paid',
                  'items')

    def get_address(self, obj):
        return Business.objects.get(id=obj.bill_from.id).address

    def get_business_name(self, obj):
        return Business.objects.get(id=obj.bill_from.id).business_name


class ReceivablesSerializer(serializers.ModelSerializer):
    invoice_id = serializers.IntegerField(source='id')
    items = OrderSerializer(many=True, read_only=True)
    address = serializers.SerializerMethodField()
    business_name = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ('invoice_id',
                  'bill_to',
                  'bill_from',
                  'business_name',
                  'address',
                  'date_sent',
                  'date_due',
                  'terms',
                  'total_price',
                  'currency',
                  'is_flagged',
                  'is_scheduled',
                  'is_paid',
                  'items')

    def get_address(self, obj):
        return Business.objects.get(id=obj.bill_to.id).address

    def get_business_name(self, obj):
        return Business.objects.get(id=obj.bill_to.id).business_name