from django.urls import path
from . import views

urlpatterns = [
    # Đảm bảo có ít nhất một đường dẫn hoặc để trống danh sách đúng chuẩn:
    # path('...', views.ten_view, name='ten_url'),
    path('profile/', views.customer_profile_view, name='customer_profile'),
    path('profile/lock/', views.customer_lock_account_view, name='customer_lock_account'),
]
