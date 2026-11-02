# chatbot/admin.py
from django.contrib import admin
from .models import KichBanChatbot, BuocChatbot, PhienHoiThoai, TinNhan, YeuCauTuVan

# 1. Tạo class Inline cho Bước Chatbot
class BuocChatbotInline(admin.TabularInline):
    model = BuocChatbot
    extra = 1  # Số dòng trống sẵn để thêm bước mới
    ordering = ('thu_tu',)

# 2. Đăng ký Kịch bản Chatbot kèm Inline
@admin.register(KichBanChatbot)
class KichBanChatbotAdmin(admin.ModelAdmin):
    list_display = ('ma_kb', 'ten_kich_ban', 'trang_thai')
    search_fields = ('ten_kich_ban',)
    inlines = [BuocChatbotInline]  # Nhúng các bước trực tiếp vào trang kịch bản

@admin.register(BuocChatbot)
class BuocChatbotAdmin(admin.ModelAdmin):
    list_display = ('ma_buoc', 'ma_kb', 'thu_tu', 'trang_thai')
    list_filter = ('ma_kb', 'trang_thai')
    ordering = ('thu_tu',)

@admin.register(PhienHoiThoai)
class PhienHoiThoaiAdmin(admin.ModelAdmin):
    list_display = ('ma_pht', 'ma_kh', 'ma_kb', 'thoi_gian_bat_dau', 'trang_thai')
    list_filter = ('trang_thai',)

@admin.register(TinNhan)
class TinNhanAdmin(admin.ModelAdmin):
    list_display = ('ma_tn', 'ma_pht', 'loai_nguoi_gui', 'thoi_gian')
    list_filter = ('loai_nguoi_gui',)

@admin.register(YeuCauTuVan)
class YeuCauTuVanAdmin(admin.ModelAdmin):
    list_display = ('ma_yctv', 'ma_pht', 'trang_thai', 'thoi_gian_yeu_cau')
    list_filter = ('trang_thai',)