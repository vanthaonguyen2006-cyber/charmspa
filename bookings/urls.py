from django.urls import path
from . import views

urlpatterns = [
    # Customer
    path('customer/', views.booking_customer_list, name='booking_customer_list'),
    path('create/', views.booking_customer_create, name='booking_customer_create'),
    path('success/', views.booking_customer_success, name='booking_customer_success'),
    path('<str:ma_lh>/', views.booking_customer_detail, name='booking_customer_detail'),
    path('<str:ma_lh>/cancel/', views.booking_customer_cancel, name='booking_customer_cancel'),
    path('<str:ma_lh>/reschedule/', views.booking_customer_reschedule, name='booking_customer_reschedule'),

    # API & Admin
    path('api/bed-availability/', views.api_check_bed_availability, name='api_kiem_tra_giuong'),
    path('admin/activity_days/', views.manage_activity_days, name='quan_ly_ngay_hoat_dong'),
    path('admin/activity_days/unlock/<str:pk>/', views.unlock_activity_day, name='mo_khoa_ngay'),
    path('admin/bookings/<str:ma_lh>/delete/', views.booking_admin_delete, name='booking_admin_delete'),
    path('staff/assign/<str:ma_lh>/', views.assign_staff_to_booking, name='assign_staff'),
    #Staff
    path('staff/bookings/create/', views.booking_staff_create, name='staff_booking_create'),
    path('staff/bookings/', views.booking_staff_list, name='staff_booking_list'),
    path('staff/bookings/<str:ma_lh>/', views.booking_staff_detail, name='staff_booking_detail'),
    path('staff/bookings/<str:ma_lh>/complete/', views.booking_staff_complete, name='staff_booking_complete'),
]
