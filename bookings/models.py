from django.db import models
from customers.models import KhachHang
from accounts.models import NhanVien, TaiKhoan
from services.models import DichVu


# Bảng lưu trạng thái từng ngày hoạt động của spa (Mở / Hoạt động / Đã khóa ngày nghỉ, bảo trì...).
class NgayHoatDong(models.Model):
    ma_nhd = models.CharField(max_length=20, primary_key=True, verbose_name="Mã ngày hoạt động")
    # unique=True để mỗi ngày chỉ có một bản ghi cấu hình ngày hoạt động.
    ngay = models.DateField(unique=True, verbose_name="Ngày")
    # Trạng thái ngày (ví dụ: 'Mở', 'Hoạt động', 'Đã khóa').
    trang_thai = models.CharField(max_length=20, verbose_name="Trạng thái")
    # Lý do khi ngày bị khóa (null/blank khi ngày mở bình thường).
    ly_do_khoa = models.CharField(max_length=255, null=True, blank=True, verbose_name="Lý do khóa")
    ngay_cap_nhat = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")
    # Đã xóa dòng ma_nv_cap_nhat ở đây!

    def __str__(self):
        if self.ly_do_khoa:
            return f"{self.ngay} - {self.trang_thai} ({self.ly_do_khoa})"
        return f"{self.ngay} - {self.trang_thai}"


# Bảng lưu thông tin lịch hẹn dịch vụ của khách hàng.
class LichHen(models.Model):
    ma_lh = models.CharField(max_length=20, primary_key=True, verbose_name="Mã lịch hẹn")
    # Khóa ngoại tới khách hàng đặt lịch; xóa khách thì xóa lịch theo.
    ma_kh = models.ForeignKey(KhachHang, on_delete=models.CASCADE, verbose_name="Khách hàng")
    # Nhân viên phụ trách chính (giữ tương thích dữ liệu cũ / hiển thị nhanh; xóa NV thì set NULL).
    ma_nv = models.ForeignKey(NhanVien, on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name="Nhân viên phụ trách")
    ma_dv = models.ForeignKey(DichVu, on_delete=models.CASCADE, verbose_name="Dịch vụ")
    ma_nhd = models.ForeignKey(NgayHoatDong, on_delete=models.CASCADE, verbose_name="Ngày hoạt động")
    ngay_hen = models.DateField(verbose_name="Ngày hẹn")
    gio_hen = models.TimeField(verbose_name="Giờ hẹn")
    # Số khách trong lịch (dùng để kiểm tra số giường trống và số nhân viên cần phân công).
    so_luong_khach = models.IntegerField(default=1, verbose_name="Số lượng khách")
    # Trạng thái vòng đời lịch hẹn ('Đã xóa' là xóa mềm, không xóa cứng khỏi DB).
    trang_thai = models.CharField(
        max_length=20,
        default='Đã đặt',
        choices=[('Đã đặt', 'Đã đặt'), ('Hoàn thành', 'Hoàn thành'),
                 ('Đã hủy', 'Đã hủy'), ('Đã xóa', 'Đã xóa')],
        verbose_name="Trạng thái"
    )
    ghi_chu = models.TextField(null=True, blank=True, verbose_name="Ghi chú")
    ngay_tao = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    # Lưu lý do hủy lịch hoặc lý do xóa mềm lịch.
    ly_do_huy = models.TextField(null=True, blank=True, verbose_name="Lý do hủy")

    def __str__(self):
        return self.ma_lh


# Bảng trung gian phân công nhiều nhân viên cho một lịch hẹn (mỗi khách/suất có thể gán 1 nhân viên).
class PhanCongLichHen(models.Model):
    ma_pclh = models.CharField(max_length=20, primary_key=True, verbose_name="Mã phân công")
    ma_lh = models.ForeignKey(LichHen, on_delete=models.CASCADE, verbose_name="Lịch hẹn")
    # Nhân viên được phân công phục vụ lịch hẹn này.
    ma_nv_phu_trach = models.ForeignKey(NhanVien, on_delete=models.CASCADE, related_name='nhan_vien_phu_trach_lh',
                                        verbose_name="Nhân viên phụ trách")
    # Tài khoản nội bộ thực hiện thao tác phân công.
    ma_nv_phan_cong = models.ForeignKey(TaiKhoan, on_delete=models.CASCADE, verbose_name="Quản trị viên phân công")
    ngay_phan_cong = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian phân công")

    def __str__(self):
        return self.ma_pclh