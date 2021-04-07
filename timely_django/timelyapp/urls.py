# users/urls.py

from django.conf.urls import url, include
from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='home'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/payables', views.PayablesJSONView.as_view(), name='payables'),
    path('dashboard/receivables', views.ReceivablesJSONView.as_view(), name='receivables'),
    path('dashboard/new_invoice', views.NewInvoiceFormView.as_view(), name='new_invoice'),
]
