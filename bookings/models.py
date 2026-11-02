from django.db import models
from customers.models import KhachHang
from accounts.models import NhanVien, TaiKhoan
from services.models import DichVu


class NgayHoatDong(models.Model):
    ma_nhd = models.CharField(max_length=20, primary_key=True, verbose_name="Mã ngày hoạt động")
    ngay = models.DateField(unique=True, verbose_name="Ngày")
    trang_thai = models.CharField(max_length=20, verbose_name="Trạng thái")
    ly_do_khoa = models.CharField(max_length=255, null=True, blank=True, verbose_name="Lý do khóa")
    ngay_cap_nhat = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")
    ma_nv_cap_nhat = models.ForeignKey(NhanVien, on_delete=models.CASCADE, null=True, blank=True,
                                       verbose_name="Nhân viên cập nhật")

    def __str__(self):
        return str(self.ngay)


class LichHen(models.Model):
    ma_lh = models.CharField(max_length=20, primary_key=True, verbose_name="Mã lịch hẹn")
    ma_kh = models.ForeignKey(KhachHang, on_delete=models.CASCADE, verbose_name="Khách hàng")
    ma_nv = models.ForeignKey(NhanVien, on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name="Nhân viên phụ trách")
    ma_dv = models.ForeignKey(DichVu, on_delete=models.CASCADE, verbose_name="Dịch vụ")
    ma_nhd = models.ForeignKey(NgayHoatDong, on_delete=models.CASCADE, verbose_name="Ngày hoạt động")
    ngay_hen = models.DateField(verbose_name="Ngày hẹn")
    gio_hen = models.TimeField(verbose_name="Giờ hẹn")
    so_luong_khach = models.IntegerField(default=1, verbose_name="Số lượng khách")
    trang_thai = models.CharField(
        max_length=20,
        default='Đã đặt',
        choices=[('Đã đặt', 'Đã đặt'), ('Đang thực hiện', 'Đang thực hiện'), ('Hoàn thành', 'Hoàn thành'),
                 ('Đã hủy', 'Đã hủy')],
        verbose_name="Trạng thái"
    )
    ghi_chu = models.TextField(null=True, blank=True, verbose_name="Ghi chú")
    ngay_tao = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    ly_do_huy = models.TextField(null=True, blank=True, verbose_name="Lý do hủy")

    def __str__(self):
        return self.ma_lh


class PhanCongLichHen(models.Model):
    ma_pclh = models.CharField(max_length=20, primary_key=True, verbose_name="Mã phân công")
    ma_lh = models.ForeignKey(LichHen, on_delete=models.CASCADE, verbose_name="Lịch hẹn")
    ma_nv_phu_trach = models.ForeignKey(NhanVien, on_delete=models.CASCADE, related_name='nhan_vien_phu_trach_lh',
                                        verbose_name="Nhân viên phụ trách")
    ma_nv_phan_cong = models.ForeignKey(TaiKhoan, on_delete=models.CASCADE, verbose_name="Quản trị viên phân công")
    ngay_phan_cong = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian phân công")

    def __str__(self):
        return self.ma_pclh