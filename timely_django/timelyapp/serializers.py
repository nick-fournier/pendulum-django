# serializers.py
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
from rest_auth.registration.serializers import RegisterSerializer
from rest_auth.serializers import LoginSerializer as RestAuthLoginSerializer
from phonenumber_field import serializerfields

from rest_framework import serializers
from .models import *

class CustomLoginSerializer(RestAuthLoginSerializer):
    username = None

class CustomRegisterSerializer(RegisterSerializer):
    username = None
    first_name = serializers.CharField(required=True, write_only=True)
    last_name = serializers.CharField(required=True, write_only=True)

    def get_cleaned_data(self):
        return {
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', ''),
        }

    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()
        adapter.save_user(request, user, self)
        setup_user_email(request, user, [])
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'date_joined']


class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        # fields = '__all__'
        exclude = ['owner', 'date_joined']

class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        # fields = '__all__'
        exclude = ['business']

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


class RawInvoiceSerializer(serializers.ModelSerializer):
    bill_from = BusinessSerializer(read_only=True)
    bill_to = BusinessSerializer(read_only=True)
    items = OrderSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = '__all__'

class InvoiceSerializer(serializers.ModelSerializer):
    invoice_id = serializers.IntegerField(source='id')
    items = OrderSerializer(many=True, read_only=True)

    from_business_name = serializers.SerializerMethodField()
    from_billing_address = serializers.SerializerMethodField()
    from_email = serializers.SerializerMethodField()
    from_phone = serializers.SerializerMethodField()

    to_business_name = serializers.SerializerMethodField()
    to_billing_address = serializers.SerializerMethodField()
    to_email = serializers.SerializerMethodField()
    to_phone = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ('invoice_id',
                  'invoice_name',

                  'bill_from_id',
                  'from_business_name',
                  'from_billing_address',
                  'from_email',
                  'from_phone',

                  'bill_to_id',
                  'to_business_name',
                  'to_billing_address',
                  'to_email',
                  'to_phone',

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

    def get_from_business_name(self, obj):
        return Business.objects.get(id=obj.bill_from.id).business_name
    def get_from_billing_address(self, obj):
        return Business.objects.get(id=obj.bill_from.id).billing_address
    def get_from_email(self, obj):
        return Business.objects.get(id=obj.bill_from.id).billing_address
    def get_from_phone(self, obj):
        return Business.objects.get(id=obj.bill_from.id).billing_address

    def get_to_business_name(self, obj):
        return Business.objects.get(id=obj.bill_to.id).business_name
    def get_to_billing_address(self, obj):
        return Business.objects.get(id=obj.bill_to.id).billing_address
    def get_to_email(self, obj):
        return Business.objects.get(id=obj.bill_to.id).billing_address
    def get_to_phone(self, obj):
        return Business.objects.get(id=obj.bill_to.id).billing_address


# OLD SERIALIZERS, MARKED FOR DELETION
## class PayablesSerializer(serializers.ModelSerializer):
#     invoice_id = serializers.IntegerField(source='id')
#     items = OrderSerializer(many=True, read_only=True)
#     billing_address = serializers.SerializerMethodField()
#     business_name = serializers.SerializerMethodField()
#
#     class Meta:
#         model = Invoice
#         fields = ('invoice_id',
#                   'invoice_name',
#                   'bill_to',
#                   'bill_from',
#                   'business_name',
#                   'billing_address',
#                   'date_sent',
#                   'date_due',
#                   'terms',
#                   'total_price',
#                   'currency',
#                   'is_flagged',
#                   'is_scheduled',
#                   'is_paid',
#                   'items')
#
#     # Update the instance
#     def update(self, instance, validated_data):
#         instance.is_flagged = validated_data['is_flagged']
#         instance.is_scheduled = validated_data['is_scheduled']
#         instance.is_paid = validated_data['is_paid']
#         instance.save()
#         return instance
#
#     def get_billing_address(self, obj):
#         return Business.objects.get(id=obj.bill_from.id).billing_address
#
#     def get_business_name(self, obj):
#         return Business.objects.get(id=obj.bill_from.id).business_name
#
# class ReceivablesSerializer(serializers.ModelSerializer):
#     invoice_id = serializers.IntegerField(source='id')
#     items = OrderSerializer(many=True, read_only=True)
#     address = serializers.SerializerMethodField()
#     business_name = serializers.SerializerMethodField()
#
#     class Meta:
#         model = Invoice
#         fields = ('invoice_id',
#                   'invoice_name',
#                   'bill_to',
#                   'bill_from',
#                   'business_name',
#                   'address',
#                   'date_sent',
#                   'date_due',
#                   'terms',
#                   'total_price',
#                   'currency',
#                   'is_flagged',
#                   'is_scheduled',
#                   'is_paid',
#                   'items')
#
#     def get_address(self, obj):
#         return Business.objects.get(id=obj.bill_to.id).address
#
#     def get_business_name(self, obj):
#         return Business.objects.get(id=obj.bill_to.id).business_name