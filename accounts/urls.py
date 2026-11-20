from django.urls import path
from . import views

urlpatterns = [
    path('dang_ky/', views.dang_ky_view, name='dang_ky'),
    path('dang_nhap/', views.dang_nhap_view, name='dang_nhap'),
    path('dang-xuat/', views.dang_xuat_view, name='dang_xuat'),
    path('change-password/', views.account_change_password_view, name='account_change_password'),
    path('staff/change-password/', views.staff_change_password_view, name='staff_change_password'),
]
