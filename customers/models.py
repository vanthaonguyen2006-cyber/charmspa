from django.db import models
from accounts.models import TaiKhoan


class HangThanhVien(models.Model):
    ma_tv = models.CharField(max_length=10, primary_key=True, verbose_name="Mã hạng thành viên")
    ten_hang = models.CharField(max_length=20, unique=True, verbose_name="Tên hạng")
    diem_toi_thieu = models.IntegerField(default=0, verbose_name="Điểm tối thiểu")
    diem_toi_da = models.IntegerField(null=True, blank=True, verbose_name="Điểm tối đa")
    ty_le_giam_gia = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Tỷ lệ giảm giá (%)")
    mo_ta_uu_dai = models.TextField(null=True, blank=True, verbose_name="Mô tả ưu đãi")

    def __str__(self):
        return self.ten_hang

    class Meta:
        db_table = "HANG_THANH_VIEN"
        verbose_name = "Hạng thành viên"
        verbose_name_plural = "Quản lý hạng thành viên"


class KhachHang(models.Model):
    ma_kh = models.CharField(max_length=20, primary_key=True, verbose_name="Mã khách hàng")
    ma_tk = models.OneToOneField(TaiKhoan, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Tài khoản", related_name="ho_so_khach_hang")
    ma_tv = models.ForeignKey(HangThanhVien, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Hạng thành viên")
    ho_ten = models.CharField(max_length=100, verbose_name="Họ và tên")
    ngay_sinh = models.DateField(null=True, blank=True, verbose_name="Ngày sinh")
    gioi_tinh = models.CharField(max_length=10, choices=[("Nam", "Nam"), ("Nữ", "Nữ"), ("Khác", "Khác")], null=True, blank=True, verbose_name="Giới tính")
    diem_tich_luy_kh = models.IntegerField(default=0, verbose_name="Điểm tích lũy")
    # Không còn sdt hay email ở đây nữa, số điện thoại đã nằm ở TaiKhoan!

    def __str__(self):
        return f"{self.ho_ten}"

    class Meta:
        db_table = "KHACH_HANG"
        verbose_name = "Khách hàng"
        verbose_name_plural = "Quản lý khách hàng"