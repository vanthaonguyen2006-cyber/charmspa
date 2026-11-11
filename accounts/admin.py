# Import công cụ quản trị của Django
from django.contrib import admin

# Import model Tài khoản
from .models import TaiKhoan, LichSuTaiKhoan, NhanVien

# Đăng ký model Tài khoản trên trang Admin
admin.site.register(TaiKhoan)
admin.site.register(LichSuTaiKhoan)
admin.site.register(NhanVien)