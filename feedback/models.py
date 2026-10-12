# feedback/models.py
from django.db import models
from customers.models import KhachHang
from services.models import DichVu
from accounts.models import NhanVien, TaiKhoan


class PhanHoiKhieuNai(models.Model):
    ma_ph = models.CharField(max_length=20, primary_key=True, verbose_name="Mã phản hồi/khiếu nại")
    ma_kh = models.ForeignKey(KhachHang, on_delete=models.CASCADE, verbose_name="Khách hàng")
    ma_dv = models.ForeignKey(DichVu, on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name="Dịch vụ liên quan")
    loai_ph = models.CharField(max_length=20, choices=[('Phản hồi', 'Phản hồi'), ('Khiếu nại', 'Khiếu nại')],
                               verbose_name="Loại")
    tieu_de = models.CharField(max_length=255, verbose_name="Tiêu đề")
    noi_dung = models.TextField(verbose_name="Nội dung chi tiết")
    trang_thai_xu_ly = models.CharField(max_length=20, default='Đã tiếp nhận', verbose_name="Trạng thái xử lý")
    tinh_hop_le = models.CharField(max_length=20, default='Hợp lệ', verbose_name="Tính hợp lệ")
    ly_do_khong_hop_le = models.CharField(max_length=255, null=True, blank=True, verbose_name="Lý do không hợp lệ")
    ngay_gui = models.DateTimeField(auto_now_add=True, verbose_name="Ngày gửi")
    ngay_giai_quyet = models.DateTimeField(null=True, blank=True, verbose_name="Ngày giải quyết")

    def __str__(self):
        return f"{self.loai_ph} - {self.tieu_de}"


class PhanCongXuLy(models.Model):
    ma_pc = models.CharField(max_length=20, primary_key=True, verbose_name="Mã phân công")
    ma_ph = models.ForeignKey(PhanHoiKhieuNai, on_delete=models.CASCADE, verbose_name="Phiếu phản hồi")
    ma_nv = models.ForeignKey(NhanVien, on_delete=models.CASCADE, verbose_name="Nhân viên xử lý")
    ma_nguoi_phan_cong = models.ForeignKey(TaiKhoan, on_delete=models.CASCADE, verbose_name="Quản trị viên phân công")
    thoi_gian_pc = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian phân công")

    def __str__(self):
        return self.ma_pc


class LichSuXuLy(models.Model):
    ma_ls = models.CharField(max_length=20, primary_key=True, verbose_name="Mã lịch sử xử lý")
    ma_ph = models.ForeignKey(PhanHoiKhieuNai, on_delete=models.CASCADE, verbose_name="Phiếu phản hồi")
    ma_nguoi_thuc_hien = models.ForeignKey(TaiKhoan, on_delete=models.CASCADE, verbose_name="Người thực hiện")
    loai_thao_tac = models.CharField(max_length=50, verbose_name="Loại thao tác")
    noi_dung = models.TextField(null=True, blank=True, verbose_name="Chi tiết thao tác")
    ngay_thuc_hien = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian")

    def __str__(self):
        return f"{self.loai_thao_tac} - {self.ma_ph}"


class TepDinhKem(models.Model):
    ma_tep = models.CharField(max_length=20, primary_key=True, verbose_name="Mã tệp")
    ma_ph = models.ForeignKey(PhanHoiKhieuNai, on_delete=models.CASCADE, verbose_name="Phiếu phản hồi")
    ten_tep = models.CharField(max_length=255, verbose_name="Tên tệp")
    duong_dan_tep = models.CharField(max_length=255, verbose_name="Đường dẫn")
    loai_tep = models.CharField(max_length=50, verbose_name="Loại tệp")
    ngay_tai_len = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tải lên")

    def __str__(self):
        return self.ten_tep


from django.db import models

# Create your models here.
