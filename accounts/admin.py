# Import công cụ quản trị của Django
from django.contrib import admin

# Import model Tài khoản và hàm kiểm tra quyền
from .models import LichSuTaiKhoan, NhanVien, TaiKhoan, can_access_django_admin

# Giới hạn Django Admin (/admin/)
admin.site.has_permission = lambda request: can_access_django_admin(request.user)

# Đăng ký model Tài khoản trên trang Admin
admin.site.register(TaiKhoan)
admin.site.register(LichSuTaiKhoan)
admin.site.register(NhanVien)
