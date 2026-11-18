from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('staff/services/', views.staff_services, name='staff_services'),
    path('staff/services/add/', views.api_them_dich_vu, name='api_them_dich_vu'),
    path('staff/services/edit/', views.api_sua_dich_vu, name='api_sua_dich_vu'),
    path('staff/services/delete/', views.api_xoa_dich_vu, name='api_xoa_dich_vu'),
    path('services/history/', views.customer_service_history_view, name='customer_service_history'),
]
