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
import allauth.account.views
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework import routers
from timelyapp import views

router = routers.DefaultRouter()
router.register(r'businesses', views.BusinessViewSet, basename='api-businesses')
router.register(r'inventory', views.InventoryViewSet, basename='api-inventory')
router.register(r'orders', views.OrderViewSet, basename='api-orders')
router.register(r'invoices', views.InvoiceViewSet, basename='api-invoices')
router.register(r'new_receivable', views.NewReceivableViewSet, basename='api-new_receivable')
router.register(r'new_payable', views.NewPayableViewSet, basename='api-new_payable')
router.register(r'new_order', views.NewOrderViewset, basename='api-new_order')
router.register(r'payables', views.PayablesViewSet, basename='api-payables')
router.register(r'receivables', views.ReceivablesViewSet, basename='api-receivables')
router.register(r'outreach', views.OutreachViewSet, basename='api-newsletter')
router.register(r'businessinfo', views.BusinessInfo, basename='api-businessinfo')
router.register(r'accountemails', views.EmailVerifyView, basename='api-accountemails')
router.register(r'notifications', views.NotificationViewSet, basename='notifications')
router.register(r'taxrates', views.TaxRatesViewSet, basename='taxrates')
router.register(r'financing_request', views.FinancingRequestViewSet, basename='financing_request')
router.register(r'download_financing_request', views.DownloadFinancingRequestViewSet, basename='financing_request_download')

# Stripe views
router.register(r'stripe/payinvoice', views.StripePayInvoice, basename='payinvoice')
router.register(r'stripe/payinvoice/confirm', views.StripeConfirmPayInvoice, basename='payinvoice-confirm')
router.register(r'stripe/onboard', views.StripeOnboard, basename='stripe-onboard')
router.register(r'stripe/paymentmethods', views.StripePaymentMethods, basename='stripe-paymentmethods')
router.register(r'stripe/paymentmethods/card', views.StripePaymentMethods, basename='stripe-paymentmethods-card')
router.register(r'stripe/paymentmethods/ach', views.StripePaymentMethods, basename='stripe-paymentmethods-ach')

# Plaid views
router.register(r'plaid/linktoken', views.PlaidLinkToken, basename='plaid-link')

user_list = views.StripePayInvoice.as_view({'get': 'list'})
user_detail = views.StripePayInvoice.as_view({'get': 'retrieve'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('timelyapp.urls')),

    # Timely Endpoints
    path('api/', include((router.urls, 'timely'), namespace='api')),  # The data API
    path('api-auth/', include('rest_framework.urls')),  # DRF auth portal
    path('api/rest-auth/', include('rest_auth.urls')),  # auth endpoint api
    path('api/rest-auth/registration/', include('rest_auth.registration.urls')),  # registration api
    # path('api/rest-auth/user/', views.UserInfo), # update user info
    path('api/account/', include('allauth.urls')),
    path('api/rest-auth/registration/account-confirm-email/<key>', allauth.account.views.confirm_email,
         name='account_confirm_email'),
    # path('api/rest-auth/password/reset/confirm/<uidb64>/<token>', allauth.account.views.password_reset_from_key, name='password_reset_confirm'),
    path('api/rest-auth/password/reset/confirm/<uidb64>/<token>', auth_views.PasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
]