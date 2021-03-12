# users/urls.py

from django.conf.urls import url, include
from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='home'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
]
