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
        exclude = ['owner', 'date_joined', 'managers', 'pref_payment']


# This provides the pre-fetched choices for the drop down
class ToBusinessKeyField(serializers.PrimaryKeyRelatedField):
    queryset = Business.objects.all()

    def get_queryset(self):
        return self.queryset.exclude(owner__id=self.context['request'].user.id)

class FromBusinessKeyField(serializers.PrimaryKeyRelatedField):
    queryset = Business.objects.all()

    def bill_from(self, value):
        if self.pk_field is not None:
            return self.pk_field.bill_from(value.pk)
        return {"id": value.pk}

    def get_queryset(self):
        return self.queryset.filter(owner__id=self.context['request'].user.id)


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        exclude = ['business']

class OrderSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['quantity_purchased', 'invoice', 'item', 'description', 'name']

    def get_name(self, obj):
        return Inventory.objects.get(id=obj.item.id).name

    def get_description(self, obj):
        return Inventory.objects.get(id=obj.item.id).description


class NewInvoiceSerializer(serializers.ModelSerializer):
    bill_to = ToBusinessKeyField()
    bill_from = FromBusinessKeyField()
    items = OrderSerializer(many=True)

    class Meta:
        model = Invoice
        fields = ['bill_to', 'bill_from', 'items', 'terms', 'currency', 'notes']

    def calculate_duedate(self, terms):
        today = datetime.date.today()
        ndays = {'NET7': 7, 'NET10': 10, 'NET30': 30, 'NET60': 60, 'NET90': 90, 'NET120': 120}

        if terms in ndays:
            return (today + datetime.timedelta(ndays[terms])).strftime("%Y-%m-%d")
        elif terms in ['COD', 'CIA']:
            return {'COD': 'On delivery', 'CIA': 'Cash in advance'}[terms]
        else:
            return None

    def generate_invoice_name(self, bill_from_id):
        name = Business.objects.get(pk=bill_from_id).business_name
        n = Invoice.objects.filter(bill_from__id=bill_from_id).count()

        words = name.split(" ")
        if len(words) > 1:
            name = ''.join([x[0] for x in words[:2]]).upper()
        else:
            name = name[:2].upper()
        name += str(datetime.date.today().year)[-2:]
        name += str(n).zfill(6)
        return name

    def calculate_prices(self, items):
        #Calculate sub-total and total price
        total_price = 0
        for i in range(len(items)):
            unit_price = getattr(Inventory.objects.get(pk=items[i]['item'].pk), 'unit_price')
            items[i] = {**items[i], **{'item_total_price': unit_price * items[i]['quantity_purchased']}}
            total_price += items[i]['item_total_price']
        return items, total_price

    # Custom create()
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        validated_data['date_sent'] = datetime.date.today()
        validated_data['date_due'] = self.calculate_duedate(validated_data['terms'])
        validated_data['invoice_name'] = self.generate_invoice_name(validated_data['bill_from'].pk)
        items_data, validated_data['total_price'] = self.calculate_prices(items_data)

        invoice = Invoice.objects.create(**validated_data)
        for item in items_data:
            item.pop('invoice', None)
            Order.objects.create(invoice=invoice, **item)
        return invoice


class FullInvoiceSerializer(serializers.ModelSerializer):
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