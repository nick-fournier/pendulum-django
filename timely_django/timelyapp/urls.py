# users/urls.py

# from django.conf.urls import url, include
from django.urls import include, path
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'invoices', views.InvoiceViewSet)

urlpatterns = [
    # path('', views.index, name='home'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/payables', views.PayablesJSONView.as_view(), name='payables'),
    path('dashboard/receivables', views.ReceivablesJSONView.as_view(), name='receivables'),
    path('dashboard/new_invoice', views.NewInvoiceFormView.as_view(), name='new_invoice'),
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
