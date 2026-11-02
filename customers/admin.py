# Import công cụ quản trị của Django
from django.contrib import admin

# Import model Khách hàng
from .models import KhachHang

# Đăng ký model Khách hàng để quản lý trên trang Admin
admin.site.register(KhachHang)