# chatbot/models.py
from django.db import models
from customers.models import KhachHang
from accounts.models import NhanVien


class KichBanChatbot(models.Model):
    ma_kb = models.CharField(max_length=10, primary_key=True, verbose_name="Mã kịch bản")
    ten_kich_ban = models.CharField(max_length=150, unique=True, verbose_name="Tên kịch bản")
    mo_ta = models.TextField(null=True, blank=True, verbose_name="Mô tả")
    trang_thai = models.CharField(max_length=30, default='Đang hoạt động', verbose_name="Trạng thái")
    # MỚI: khớp cột NgayCapNhat trong báo cáo, tự cập nhật mỗi lần lưu
    ngay_cap_nhat = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name="Ngày cập nhật")

    class Meta:
        verbose_name = "Kịch bản Chatbot"
        verbose_name_plural = "Kịch bản Chatbot"

    def __str__(self):
        return self.ten_kich_ban


class BuocChatbot(models.Model):
    ma_buoc = models.CharField(max_length=10, primary_key=True, verbose_name="Mã bước")
    ma_kb = models.ForeignKey(KichBanChatbot, on_delete=models.CASCADE, verbose_name="Kịch bản")
    # MỚI: tên bước (trước đây view và template dùng nhưng model chưa có)
    ten_buoc = models.CharField(max_length=150, blank=True, default='', verbose_name="Tên bước")
    noi_dung = models.TextField(verbose_name="Nội dung bước")
    thu_tu = models.IntegerField(verbose_name="Thứ tự bước")
    trang_thai = models.CharField(max_length=30, default='Đang hoạt động', verbose_name="Trạng thái")

    class Meta:
        verbose_name = "Bước Chatbot"
        verbose_name_plural = "Bước Chatbot"

    def __str__(self):
        return f"Bước {self.thu_tu} - {self.ma_kb}"


class SoDoKichBan(models.Model):
    """MỚI: sơ đồ kéo thả của một kịch bản (các hộp, tọa độ, nút lựa chọn, đường nối) dạng JSON.
    Bảng KICH_BAN_CHATBOT và BUOC_CHATBOT trong báo cáo được giữ nguyên;
    khi bấm Lưu, các hộp được đồng bộ sang BUOC_CHATBOT."""
    kich_ban = models.OneToOneField(KichBanChatbot, on_delete=models.CASCADE,
                                    related_name='so_do', verbose_name="Kịch bản")
    du_lieu = models.JSONField(default=dict, verbose_name="Dữ liệu sơ đồ")
    ngay_cap_nhat = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")

    class Meta:
        verbose_name = "Sơ đồ kịch bản"
        verbose_name_plural = "Sơ đồ kịch bản"

    def __str__(self):
        return f"Sơ đồ {self.kich_ban_id}"


class PhienHoiThoai(models.Model):
    ma_pht = models.CharField(max_length=10, primary_key=True, verbose_name="Mã phiên hội thoại")
    ma_kh = models.ForeignKey(KhachHang, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Khách hàng")
    # ĐÃ SỬA: Cho phép null=True, blank=True để không bị lỗi CSDL khi chưa tạo kịch bản
    ma_kb = models.ForeignKey(KichBanChatbot, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Kịch bản")
    thoi_gian_bat_dau = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian bắt đầu")
    thoi_gian_ket_thuc = models.DateTimeField(null=True, blank=True, verbose_name="Thời gian kết thúc")
    trang_thai = models.CharField(max_length=30, default='Đang xử lý', verbose_name="Trạng thái")
    ket_qua_xu_ly = models.CharField(max_length=255, null=True, blank=True, verbose_name="Kết quả xử lý")

    class Meta:
        verbose_name = "Phiên hội thoại"
        verbose_name_plural = "Phiên hội thoại"

    def __str__(self):
        return self.ma_pht


class TinNhan(models.Model):
    ma_tn = models.CharField(max_length=10, primary_key=True, verbose_name="Mã tin nhắn")
    ma_pht = models.ForeignKey(PhienHoiThoai, on_delete=models.CASCADE, verbose_name="Phiên hội thoại")
    ma_nv = models.ForeignKey(NhanVien, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Nhân viên gửi")
    ma_buoc = models.ForeignKey(BuocChatbot, on_delete=models.SET_NULL, null=True, blank=True,
                                verbose_name="Bước chatbot gửi")
    loai_nguoi_gui = models.CharField(max_length=20, choices=[('Khách hàng', 'Khách hàng'), ('Chatbot', 'Chatbot'),
                                                              ('Nhân viên', 'Nhân viên')],
                                      verbose_name="Loại người gửi")
    noi_dung = models.TextField(verbose_name="Nội dung tin nhắn")
    thoi_gian = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian")

    class Meta:
        verbose_name = "Tin nhắn"
        verbose_name_plural = "Tin nhắn"

    def __str__(self):
        return f"{self.loai_nguoi_gui}: {self.noi_dung[:30]}"


class YeuCauTuVan(models.Model):
    ma_yctv = models.CharField(max_length=10, primary_key=True, verbose_name="Mã yêu cầu tư vấn")
    ma_pht = models.ForeignKey(PhienHoiThoai, on_delete=models.CASCADE, verbose_name="Phiên hội thoại")
    ma_nv = models.ForeignKey(NhanVien, on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name="Nhân viên tiếp nhận")
    noi_dung = models.TextField(verbose_name="Nội dung yêu cầu")
    thoi_gian_yeu_cau = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian yêu cầu")
    trang_thai = models.CharField(max_length=30, default='Chờ xử lý', verbose_name="Trạng thái")
    # MỚI: khớp các cột ThoiGianTiepNhan / ThoiGianHoanTat trong báo cáo, kèm tên người tiếp nhận và ghi chú xử lý
    nguoi_tiep_nhan = models.CharField(max_length=100, blank=True, default='', verbose_name="Người tiếp nhận")
    thoi_gian_tiep_nhan = models.DateTimeField(null=True, blank=True, verbose_name="Thời gian tiếp nhận")
    thoi_gian_hoan_tat = models.DateTimeField(null=True, blank=True, verbose_name="Thời gian hoàn tất")
    ghi_chu_xu_ly = models.TextField(blank=True, default='', verbose_name="Ghi chú xử lý")

    class Meta:
        verbose_name = "Yêu cầu tư vấn"
        verbose_name_plural = "Yêu cầu tư vấn"

    def __str__(self):
        return self.ma_yctv
