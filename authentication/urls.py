from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path

from authentication import views

app_name = 'authentication'

urlpatterns = [
    path('', views.CustomLoginView.as_view(), name='login'),
    path('admin/login/', views.CustomLoginView.as_view(), name='admin_login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profil/', views.profil, name='profil'),
]