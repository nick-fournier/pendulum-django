from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.shortcuts import render
from django.core.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from .stripe_views import *

from pyzipcode import ZipCodeDatabase

from rest_framework.viewsets import ReadOnlyModelViewSet
from drf_renderer_xlsx.mixins import XLSXFileMixin
from drf_renderer_xlsx.renderers import XLSXRenderer
from rest_framework_csv.renderers import CSVRenderer

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
        #queryset = Invoice.objects.filter(bill_from__id=business_id).order_by('date_due')
        queryset = None
        return queryset

class NewPayableViewSet(viewsets.ModelViewSet):
    serializer_class = NewPayableSerializer

    def get_queryset(self):
        business_id = self.request.user.business.id
        #queryset = Invoice.objects.filter(bill_to__id=business_id).order_by('date_due')
        queryset = None
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

class NotificationViewSet(mixins.ListModelMixin,
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
            send_notification(**data)

        return Response(status=status.HTTP_200_OK,
                        data={'Success': data['notif_type'] + ' notification sent for invoice ' + data['invoice_id']})

class TaxRatesViewSet(mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.CreateModelMixin,
                      mixins.DestroyModelMixin,
                      viewsets.GenericViewSet):

    serializer_class = TaxRateSerializer

    def get_queryset(self):
        return Taxes.objects.filter(business=self.request.user.business.id)

    def create(self, request):
        data = request.data.copy()

        # Remove blank elements
        for place in ['zipcode', 'city', 'state']:
            if data[place] == "" or data[place] is None:
                data.pop(place)

        if 'zipcode' in data:
            zipdata = ZipCodeDatabase()[data['zipcode']]

            data.update(
                {
                    "city": zipdata.city,
                    "state": zipdata.state,
                    "country": 'US',
                }
            )

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(business=self.request.user.business)

class FinancingRequestViewSet(mixins.CreateModelMixin,
                              mixins.ListModelMixin,
                              mixins.RetrieveModelMixin,
                              viewsets.GenericViewSet):

    serializer_class = FinancingRequestSerializer

    def get_queryset(self):
        return FinancingRequests.objects.filter(business=self.request.user.business.id)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fin_request = FinancingRequests.objects.filter(Q(business=self.request.user.business) &
                                                       Q(invoice_id=self.request.data['invoice_id']))
        if fin_request.exists():
            return Response(status=status.HTTP_200_OK,
                            data={'OK': 'Financing already requested on this invoice by this user.'}
                            )
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        invoice = Invoice.objects.get(id=self.request.data['invoice_id'])
        fin_type = 'PAYOUT' if invoice.bill_from.id == self.request.user.business.id else 'PAYLATER'
        data = {
            "business": self.request.user.business,
            "request_by": self.request.user,
            "invoice": invoice,
            "financing_type": fin_type
        }
        serializer.save(**data)


class DownloadFinancingRequestViewSet(XLSXFileMixin, ReadOnlyModelViewSet):
    serializer_class = FinancingRequestSerializer
    renderer_classes = [CSVRenderer] #XLSXRenderer
    filename = 'financing_requests_{}.xlsx'.format(str(datetime.date.today()))
    queryset = FinancingRequests.objects.all()
