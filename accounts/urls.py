from django.urls import path
from . import views

urlpatterns = [
    # Đường dẫn xử lý trang đăng ký (Truy cập qua: /accounts/dang-ky/)
    path('dang_ky/', views.dang_ky_view, name='dang_ky'),
    path('dang_nhap/', views.dang_nhap_view, name='dang_nhap'),
    path('dang-xuat/', views.dang_xuat_view, name='dang_xuat'),
]