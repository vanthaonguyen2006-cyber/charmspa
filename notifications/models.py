from django.db import models
from django.utils import timezone
from accounts.models import NhanVien
from services.models import DichVu
from bookings.models import LichHen
from customers.models import KhachHang


class ChuongTrinhUuDai(models.Model):
    ma_ctud = models.CharField(max_length=10, primary_key=True, verbose_name="Mã ưu đãi")
    ten_chuong_trinh = models.CharField(max_length=200, verbose_name="Tên chương trình")
    mo_ta = models.TextField(null=True, blank=True, verbose_name="Mô tả")

    # Bổ sung các trường chi tiết
    loai_uu_dai = models.CharField(max_length=50, null=True, blank=True, verbose_name="Loại ưu đãi")
    gia_tri_uu_dai = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Giá ưu đãi")
    gia_goc = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Giá gốc")
    thoi_luong = models.CharField(max_length=50, default="90 phút", verbose_name="Thời lượng liệu trình")
    doi_tuong_ap_dung = models.CharField(max_length=100, default="Tất cả khách hàng", verbose_name="Đối tượng áp dụng")
    dia_diem_ap_dung = models.CharField(max_length=200, default="Charm Grand Spa & Wellness",
                                        verbose_name="Địa điểm áp dụng")

    ngay_bat_dau = models.DateTimeField(verbose_name="Ngày bắt đầu")
    ngay_ket_thuc = models.DateTimeField(verbose_name="Ngày kết thúc")

    quyen_loi = models.TextField(null=True, blank=True, verbose_name="Quyền lợi khách hàng")
    dieu_kien = models.TextField(null=True, blank=True, verbose_name="Điều kiện áp dụng")

    hinh_anh = models.CharField(max_length=500, null=True, blank=True, verbose_name="Hình ảnh Banner URL")
    trang_thai = models.CharField(max_length=30, default='Đang áp dụng', verbose_name="Trạng thái")

    def __str__(self):
        return self.ten_chuong_trinh


class HuongDanChamSoc(models.Model):
    ma_hd = models.CharField(max_length=10, primary_key=True, verbose_name="Mã hướng dẫn")
    ma_dv = models.ForeignKey('services.DichVu', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Dịch vụ áp dụng")
    tieu_de = models.CharField(max_length=150, verbose_name="Tiêu đề")
    noi_dung = models.TextField(verbose_name="Nội dung hướng dẫn")
    trang_thai = models.CharField(max_length=30, default='Hoạt động', verbose_name="Trạng thái")

    def __str__(self):
        return self.tieu_de


class ThongBao(models.Model):
    ma_tb = models.CharField(max_length=10, primary_key=True, verbose_name="Mã thông báo")
    ma_lh = models.ForeignKey(LichHen, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Lịch hẹn")
    ma_ctud = models.ForeignKey(ChuongTrinhUuDai, on_delete=models.SET_NULL, null=True, blank=True,
                                verbose_name="Chương trình ưu đãi")
    ma_nv = models.ForeignKey(NhanVien, on_delete=models.CASCADE, verbose_name="Nhân viên tạo")
    loai_tb = models.CharField(max_length=50, verbose_name="Loại thông báo")
    tieu_de = models.CharField(max_length=200, verbose_name="Tiêu đề")
    noi_dung = models.TextField(verbose_name="Nội dung")
    thoi_gian_tao = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian tạo")
    trang_thai = models.CharField(max_length=30, default='Chưa gửi', verbose_name="Trạng thái")

    def __str__(self):
        return self.tieu_de


class ThongBaoKhachHang(models.Model):
    ma_tbkh = models.CharField(max_length=10, primary_key=True, verbose_name="Mã chi tiết thông báo KH")
    ma_tb = models.ForeignKey(ThongBao, on_delete=models.CASCADE, verbose_name="Thông báo")
    ma_kh = models.ForeignKey(KhachHang, on_delete=models.CASCADE, verbose_name="Khách hàng nhận")
    thoi_gian_gui = models.DateTimeField(null=True, blank=True, verbose_name="Thời gian gửi")
    trang_thai_gui = models.CharField(max_length=30, default='Chưa gửi', verbose_name="Trạng thái gửi")


# ==============================================================================
# BỔ SUNG: BẢNG NHẬT KÝ GỬI HDCS (LƯU VÂN HÀNH KHI KHÁCH CHECKOUT TỪ LỊCH HẸN)
# ==============================================================================
class NhatKyGuiHDCS(models.Model):
    ma_lh = models.ForeignKey(LichHen, on_delete=models.CASCADE, verbose_name="Lịch hẹn liên quan")
    ma_hd = models.ForeignKey(HuongDanChamSoc, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Mẫu hướng dẫn")
    ten_khach_hang = models.CharField(max_length=255, verbose_name="Tên khách hàng")
    ten_dich_vu = models.CharField(max_length=255, verbose_name="Tên dịch vụ")
    ten_ktv = models.CharField(max_length=100, null=True, blank=True, verbose_name="Kỹ thuật viên thực hiện")
    gio_checkout = models.DateTimeField(default=timezone.now, verbose_name="Thời gian hoàn thành (Checkout)")
    trang_thai = models.BooleanField(default=False, verbose_name="Trạng thái gửi HDCS (True: Đã gửi, False: Chưa gửi)")
    noi_dung_gui = models.TextField(null=True, blank=True, verbose_name="Nội dung lời dặn thực tế đã gửi")
    thoi_gian_gui = models.DateTimeField(null=True, blank=True, verbose_name="Thời gian bấm gửi")

    class Meta:
        verbose_name = "Nhật ký gửi HDCS"
        verbose_name_plural = "Nhật ký gửi HDCS"
        ordering = ['-gio_checkout']

    def __str__(self):
        return f"{self.ten_khach_hang} - {self.ten_dich_vu}"