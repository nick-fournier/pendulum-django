# serializers.py

from rest_framework import serializers
from .models import *

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'date_joined']

class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = '__all__'

    def get_name(self, obj):
        return Inventory.objects.get(id=obj.item.id).name

    def get_description(self, obj):
        return Inventory.objects.get(id=obj.item.id).description


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
                  'invoice_name',
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

    # Update the instance
    def update(self, instance, validated_data):
        instance.is_flagged = validated_data['is_flagged']
        instance.is_scheduled = validated_data['is_scheduled']
        instance.is_paid = validated_data['is_paid']
        instance.save()
        return instance

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
                  'invoice_name',
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