# serializers.py
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
from rest_auth.registration.serializers import RegisterSerializer
from rest_auth.serializers import LoginSerializer as RestAuthLoginSerializer
from phonenumber_field import serializerfields
from django.db.models.query_utils import Q

from rest_framework import serializers
from .models import *
from timelyapp.utils import calculate_duedate, generate_invoice_name, get_business_id

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
    billing_address = serializers.CharField(read_only=True)
    shipping_address = serializers.CharField(read_only=True)
    class Meta:
        model = Business
        exclude = ['owner', 'date_joined', 'managers']


# This provides the pre-fetched choices for the drop down
class ToBusinessKeyField(serializers.PrimaryKeyRelatedField):
    queryset = Business.objects.all()

    def get_queryset(self):
        return self.queryset.exclude(owner__id=self.context['request'].user.id)


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'


class NewOrderSerializer(serializers.ModelSerializer):
    is_new = serializers.BooleanField(default=False)
    class Meta:
        model = Order
        fields = ['item_name', 'quantity_purchased', 'item_price', 'item_total_price', 'is_new']


class NewInvoiceSerializer(serializers.ModelSerializer):
    bill_to_key = ToBusinessKeyField(source="bill_to")
    bill_to_name = serializers.SerializerMethodField(required=False)
    items = NewOrderSerializer(many=True, allow_null=True, required=False)

    class Meta:
        model = Invoice
        fields = ['bill_to_key', 'bill_to_name', 'terms', 'date_due', 'invoice_total_price', 'accepted_payments', 'notes',
                  'items']

    def get_bill_to_name(self, obj):
        return Business.objects.get(id=obj.bill_to.id).business_name

    # Custom create()
    def create(self, validated_data):
        # validated_data['bill_to'] = validated_data.pop('bill_to_key')
        validated_data['bill_from'] = Business.objects.get(owner__id=self.context['request'].user.id)
        validated_data['date_sent'] = datetime.date.today()
        validated_data['date_due'] = calculate_duedate(validated_data['terms'])
        validated_data['invoice_name'] = generate_invoice_name(validated_data['bill_from'].pk)

        # Pop out many-to-many payment field. Need to create invoice before assigning
        accepted_payments = validated_data.pop('accepted_payments')

        # If itemized, pop out. Need to create invoice before linking
        if 'items' in validated_data:
            items_data = validated_data.pop('items')
            validated_data['invoice_only'] = False

            # Calculate total price if missing
            if not validated_data['total_price']:
                validated_data['invoice_total_price'] = 0
                for i in range(len(items_data)):
                    validated_data['invoice_total_price'] += items_data[i]['item_total_price']

            # Now create invoice and assign linked orders
            invoice = Invoice.objects.create(**validated_data)

            for item in items_data:
                # If new item, add to inventory
                if item['is_new']:
                    new_item = {'item_name': item['item_name'], 'item_price': item['item_price']}
                    Inventory.objects.create(business=validated_data['bill_from'], **new_item)
                item.pop('is_new')
                Order.objects.create(invoice=invoice, **item)
        else:
            validated_data['invoice_only'] = True
            invoice = Invoice.objects.create(**validated_data)

        #Once invoice is created, assign payment M2M field
        for payment in accepted_payments:
            invoice.accepted_payments.add(payment)

        return invoice


class FullInvoiceSerializer(serializers.ModelSerializer):
    bill_from = BusinessSerializer(read_only=True)
    bill_to = BusinessSerializer(read_only=True)
    items = OrderSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = '__all__'

# INVOICE SERIALIZER FOR PAYABLES / RECEIVABLES
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
        return str(Business.objects.get(id=obj.bill_from.id).billing_address)
    def get_from_email(self, obj):
        return Business.objects.get(id=obj.bill_from.id).email
    def get_from_phone(self, obj):
        return str(Business.objects.get(id=obj.bill_from.id).phone)

    def get_to_business_name(self, obj):
        return Business.objects.get(id=obj.bill_to.id).business_name
    def get_to_billing_address(self, obj):
        return str(Business.objects.get(id=obj.bill_to.id).billing_address)
    def get_to_email(self, obj):
        return Business.objects.get(id=obj.bill_to.id).email
    def get_to_phone(self, obj):
        return str(Business.objects.get(id=obj.bill_to.id).phone)


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