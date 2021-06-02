# timelyapp/urls.py

from django.urls import path
from django.views.generic.base import TemplateView
from .views import redirect_view

urlpatterns = [
    path('', redirect_view)
    # path('', TemplateView.as_view(template_name='helloworld.html'), name='home')
]
