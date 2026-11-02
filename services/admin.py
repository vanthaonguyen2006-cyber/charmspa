from django.contrib import admin
from .models import DichVu, DichVuDaSuDung

@admin.register(DichVu)
class DichVuAdmin(admin.ModelAdmin):
    list_display = ('ma_dv', 'ten_dich_vu', 'loai_dich_vu', 'gia_dich_vu', 'thoi_luong', 'suc_chua_toi_da')
    search_fields = ('ma_dv', 'ten_dich_vu')

@admin.register(DichVuDaSuDung)
class DichVuDaSuDungAdmin(admin.ModelAdmin):
    list_display = ('ma_sd', 'ma_kh', 'ma_nv', 'ma_dv', 'ngay_su_dung')