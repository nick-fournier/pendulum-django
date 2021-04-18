# timelyapp/urls.py

from django.urls import include, path
from django.views.generic.base import TemplateView
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r'invoices', views.InvoiceViewSet)
router.register(r'payables', views.PayablesViewSet, basename='api-payables')
router.register(r'receivables', views.ReceivablesViewSet, basename='api-receivables')

urlpatterns = [
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('new_business/', views.NewBusinessFormView.as_view(), name='new_business'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    # path('dashboard/payables/', views.PayablesJSONView.as_view(), name='payables'),
    # path('dashboard/receivables/', views.ReceivablesJSONView.as_view(), name='receivables'),
    path('dashboard/payables/', views.PayablesView.as_view(), name='payables'),
    path('dashboard/receivables/', views.ReceivablesView.as_view(), name='receivables'),
    path('dashboard/new_invoice/', views.NewInvoiceFormView.as_view(), name='new_invoice'),
    path('rest-api/', include((router.urls, 'timely'), namespace='api')),
    # path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
