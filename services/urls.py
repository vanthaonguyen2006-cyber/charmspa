from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('staff/services/', views.staff_services, name='staff_services'),
    path('staff/services/add/', views.api_them_dich_vu, name='api_them_dich_vu'),
    path('staff/services/edit/', views.api_sua_dich_vu, name='api_sua_dich_vu'),
]