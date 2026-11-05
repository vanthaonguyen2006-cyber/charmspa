
from django.urls import path
from . import views

urlpatterns = [
    # Quản lý khách hàng dành cho nhân viên
    path('staff/customer/add/', views.staff_customer_add_view, name='staff_customer_add'),
    path('staff/customer_list/', views.staff_customer_list_view, name='staff_customer_list'),
    path('staff/customer/<str:ma_kh>/', views.staff_customer_detail_view, name='staff_customer_detail'),
    path('staff/customer/<str:ma_kh>/record-service/', views.staff_customer_record_service_view, name='staff_customer_record_service'),

    # Hồ sơ và trạng thái tài khoản khách hàng
    path('profile/', views.customer_profile_view, name='customer_profile'),
    path('profile/lock/', views.customer_lock_account_view, name='customer_lock_account'),
    path('profile/locked/', views.account_locked_view, name='account_locked'),

    # Quản lý tài khoản dành cho nhân viên
    path('staff/account_list/', views.staff_account_list_view, name='staff_account_list'),
    path('staff/account/add/', views.staff_account_add_staff_view, name='staff_account_add_staff'),
    path('staff/account/<str:ma_tk>/', views.staff_account_detail_view, name='staff_account_detail'),
    path('staff/account/toggle/<str:ma_tk>/', views.staff_toggle_account_status_view, name='staff_toggle_account'),
    path('staff/account/edit/<str:ma_tk>/', views.staff_account_edit_view, name='staff_account_edit'),
]
