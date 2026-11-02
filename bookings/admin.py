from django.contrib import admin
from .models import NgayHoatDong, LichHen, PhanCongLichHen

@admin.register(NgayHoatDong)
class NgayHoatDongAdmin(admin.ModelAdmin):
    list_display = ('ma_nhd', 'ngay', 'trang_thai', 'ly_do_khoa', 'ngay_cap_nhat')
    search_fields = ('ma_nhd', 'ly_do_khoa')
    list_filter = ('trang_thai', 'ngay')


@admin.register(LichHen)
class LichHenAdmin(admin.ModelAdmin):
    list_display = ('ma_lh', 'ma_kh', 'ma_dv', 'ngay_hen', 'gio_hen', 'so_luong_khach', 'trang_thai', 'ngay_tao')
    search_fields = ('ma_lh', 'ma_kh__ho_ten', 'ghi_chu')
    list_filter = ('trang_thai', 'ngay_hen', 'ma_dv')


@admin.register(PhanCongLichHen)
class PhanCongLichHenAdmin(admin.ModelAdmin):
    list_display = ('ma_pclh', 'ma_lh', 'ma_nv_phu_trach', 'ma_nv_phan_cong', 'ngay_phan_cong')
    search_fields = ('ma_pclh', 'ma_lh__ma_lh')
    list_filter = ('ngay_phan_cong',)