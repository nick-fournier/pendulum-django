# timelyapp/urls.py
from .views import redirect_view
from django.urls import path


urlpatterns = [
    path('', redirect_view),
]
