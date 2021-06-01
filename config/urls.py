"""config URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from allauth.account.views import confirm_email
from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken import views

from rest_framework import routers
from timelyapp import views

router = routers.DefaultRouter()
router.register(r'businesses', views.BusinessViewSet, basename='api-businesses')
router.register(r'inventory', views.InventoryViewSet, basename='api-inventory')
router.register(r'orders', views.OrderViewSet, basename='api-orders')
router.register(r'invoices', views.InvoiceViewSet, basename='api-invoices')
router.register(r'new_invoices', views.NewInvoiceViewSet, basename='api-new_invoice')
router.register(r'payables', views.PayablesViewSet, basename='api-payables')
router.register(r'receivables', views.ReceivablesViewSet, basename='api-receivables')
router.register(r'newsletter', views.NewsletterViewSet, basename='api-newsletter')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('timelyapp.urls')),

    #Endpoints
    path('api/', include((router.urls, 'timely'), namespace='api')), #The data API
    path('api-auth/', include('rest_framework.urls')), # DRF auth portal
    path('api/rest-auth/', include('rest_auth.urls')), # auth endpoint api
    path('api/rest-auth/registration/', include('rest_auth.registration.urls')), # registration api
]

