from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.shortcuts import render
from rest_framework.permissions import AllowAny
from .stripe_views import *

def chart_view(request):
    return render(request, 'chart.html')

# Create your views here.
def redirect_view(request):
    response = redirect('/api/')
    return response


class EmailVerifyView(viewsets.ReadOnlyModelViewSet):
    serializer_class = EmailVerifySerializer

    def get_queryset(self):
        return EmailAddress.objects.filter(user_id=self.request.user.id)

class BusinessInfo(viewsets.ModelViewSet):
    serializer_class = BusinessInfoSerializer

    def get_queryset(self):
        try:
            queryset = Business.objects.filter(id=self.request.user.business.id)
        except Business.DoesNotExist:
            queryset = []

        # Checking if data is current
        # account_info = stripe.Account.retrieve(queryset.get().stripe_act_id)
        # print(account_info)
        # print(queryset)

        return queryset

class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FullInvoiceSerializer

    def get_queryset(self):
        business_id = self.request.user.business.id
        queryset = Invoice.objects.filter(Q(bill_from__id=business_id) | Q(bill_to__id=business_id)).order_by('id')
        return queryset

class NewReceivableViewSet(viewsets.ModelViewSet):
    serializer_class = NewReceivableSerializer

    def get_queryset(self):
        business_id = self.request.user.business.id
        queryset = Invoice.objects.filter(bill_from__id=business_id).order_by('date_due')
        return queryset

class NewPayableViewSet(viewsets.ModelViewSet):
    serializer_class = NewPayableSerializer

    def get_queryset(self):
        business_id = self.request.user.business.id
        queryset = Invoice.objects.filter(bill_to__id=business_id).order_by('date_due')
        return queryset

class BusinessViewSet(viewsets.ModelViewSet):
    serializer_class = BusinessSerializer
    queryset = Business.objects.all()

class InventoryViewSet(viewsets.ModelViewSet):
    serializer_class = InventorySerializer

    def get_queryset(self):
        business_id = self.request.user.business.id
        queryset = Inventory.objects.filter(Q(business__id=business_id)).order_by('last_updated')
        return queryset

class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer

    def get_queryset(self):
        business_id = self.request.user.business.id
        invoice_list = Invoice.objects.filter(bill_from__id=business_id)
        queryset = Order.objects.filter(invoice__in=invoice_list)
        return queryset

class PayablesViewSet(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.CreateModelMixin,
                         viewsets.GenericViewSet):

    serializers = {
        'default': NewPayableSerializer,
        'list': InvoiceListSerializer,
        'update': InvoiceSerializer,
        'partial_update': InvoiceSerializer
    }

    def get_serializer_class(self):
        print(self.action)
        return self.serializers.get(self.action, self.serializers['default'])

    def get_queryset(self):
        business_id = self.request.user.business.id
        queryset = Invoice.objects.filter(bill_to__id=business_id).filter(is_deleted=False).order_by('date_due')
        return queryset

    def list(self, request):
        #serializer = InvoiceListSerializer(self.get_queryset(), many=True) # use this for meta data only
        serializer = InvoiceSerializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        serializer = InvoiceSerializer(Invoice.objects.filter(pk=pk), many=True)
        return Response(serializer.data)


class ReceivablesViewSet(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.CreateModelMixin,
                         viewsets.GenericViewSet):

    serializers = {
        'default': NewReceivableSerializer,
        'list': InvoiceListSerializer,
        'update': InvoiceSerializer,
        'partial_update': InvoiceSerializer
    }

    def get_serializer_class(self):
        print(self.action)
        return self.serializers.get(self.action, self.serializers['default'])

    def get_queryset(self):
        business_id = self.request.user.business.id
        queryset = Invoice.objects.filter(bill_from__id=business_id).filter(is_deleted=False).order_by('date_due')
        return queryset

    def list(self, request):
        #serializer = InvoiceListSerializer(self.get_queryset(), many=True) # use this for meta data only
        serializer = InvoiceSerializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        serializer = InvoiceSerializer(Invoice.objects.filter(pk=pk), many=True)
        return Response(serializer.data)


class OutreachViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = OutreachSerializer
    queryset = Outreach.objects.none()
    success_url = reverse_lazy('home')
    throttle_scope = 'outreach'

class NotificationViewset(mixins.ListModelMixin,
                          mixins.CreateModelMixin,
                          viewsets.GenericViewSet):

    serializer_class = NotificationSerializer
    # queryset = Invoice.objects.none()
    throttle_scope = 'remind'
    actions = ['remind']

    def list(self, request):
        actions = {
            'notification types': {'remind': 'Sends reminder email to payee account of invoice.'}
                   }
        return Response(status=status.HTTP_200_OK, data=actions)


    def create(self, request):
        data = request.data

        business_id = self.request.user.business.id
        if not Invoice.objects.filter(bill_from__id=business_id).filter(pk=data['invoice_id']).exists():
            return Response({'invoice not found.'}, status=status.HTTP_404_NOT_FOUND)

        if data['notif_type'] not in self.actions:
            return Response({'bad action type.'}, status=status.HTTP_404_NOT_FOUND)

        if data['notif_type'] == 'remind':
            #send_notification(invoice_id=data['invoice_id'], notif_type='remind', **data)
            send_notification(**data)

        return Response(status=status.HTTP_200_OK,
                        data={'Success': data['notif_type'] + ' notification sent for invoice ' + data['invoice_id']})
