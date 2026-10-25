from django.contrib import admin
from .models import KichBanChatbot, BuocChatbot, PhienHoiThoai, TinNhan, YeuCauTuVan

# Tùy chỉnh tiêu đề giao diện Trang Quản trị
admin.site.site_header = "Charm Grand Spa - Quản trị hệ thống"
admin.site.site_title = "Charm Grand Spa Admin"
admin.site.index_title = "Bảng điều khiển quản trị"

# Inline hiển thị các bước của kịch bản ngay trong trang Kịch bản
class BuocChatbotInline(admin.TabularInline):
    model = BuocChatbot
    extra = 1

@admin.register(KichBanChatbot)
class KichBanChatbotAdmin(admin.ModelAdmin):
    list_display = ('ma_kb', 'ten_kich_ban', 'trang_thai')
    search_fields = ('ten_kich_ban',)
    inlines = [BuocChatbotInline]

@admin.register(PhienHoiThoai)
class PhienHoiThoaiAdmin(admin.ModelAdmin):
    list_display = ('ma_pht', 'ma_kh', 'ma_kb', 'thoi_gian_bat_dau', 'trang_thai')
    list_filter = ('trang_thai',)

@admin.register(TinNhan)
class TinNhanAdmin(admin.ModelAdmin):
    # Đã sửa 'phien_hoi_thoai' thành 'ma_pht' để khớp với models.py
    list_display = ('ma_tn', 'ma_pht', 'loai_nguoi_gui', 'noi_dung', 'thoi_gian')
    list_filter = ('loai_nguoi_gui',)

@admin.register(YeuCauTuVan)
class YeuCauTuVanAdmin(admin.ModelAdmin):
    list_display = ('ma_yctv', 'ma_pht', 'ma_nv', 'thoi_gian_yeu_cau', 'trang_thai')
    list_filter = ('trang_thai',)