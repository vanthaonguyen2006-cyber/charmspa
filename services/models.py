# services/models.py
from django.db import models
from customers.models import KhachHang
from accounts.models import NhanVien


class DichVu(models.Model):
    ma_dv = models.CharField(max_length=20, primary_key=True, verbose_name="Mã dịch vụ")
    ten_dich_vu = models.CharField(max_length=100, verbose_name="Tên dịch vụ")
    loai_dich_vu = models.CharField(max_length=50, verbose_name="Loại dịch vụ")
    mo_ta = models.TextField(null=True, blank=True, verbose_name="Mô tả")
    thoi_luong = models.IntegerField(verbose_name="Thời lượng (phút)")
    suc_chua_toi_da = models.IntegerField(verbose_name="Sức chứa tối đa")
    diem_tich_luy_dich_vu = models.IntegerField(default=0, verbose_name="Điểm tích lũy dịch vụ")
    gia_dich_vu = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Giá dịch vụ")

    def __str__(self):
        return self.ten_dich_vu


class DichVuDaSuDung(models.Model):
    ma_sd = models.CharField(max_length=10, primary_key=True, verbose_name="Mã sử dụng")
    ma_kh = models.ForeignKey(KhachHang, on_delete=models.CASCADE, verbose_name="Khách hàng")
    ma_nv = models.ForeignKey(NhanVien, on_delete=models.CASCADE, verbose_name="Nhân viên thực hiện")
    ma_dv = models.ForeignKey(DichVu, on_delete=models.CASCADE, verbose_name="Dịch vụ")
    ngay_su_dung = models.DateTimeField(auto_now_add=True, verbose_name="Ngày sử dụng")

    def __str__(self):
        return f"{self.ma_kh} - {self.ma_dv}"


from django.db import models

# Create your models here.
