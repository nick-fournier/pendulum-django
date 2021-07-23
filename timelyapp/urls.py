# timelyapp/urls.py

from django.urls import path
from django.views.generic.base import TemplateView
from .views import redirect_view
from django.conf.urls import url
from timelyapp import views

urlpatterns = [
    path('', redirect_view),
]
