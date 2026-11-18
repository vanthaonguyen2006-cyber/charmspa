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

    # Bổ sung: liên kết tùy chọn để phân biệt lượt ghi nhận thủ công
    # và lượt ghi nhận từ một Booking cụ thể. Không ảnh hưởng dữ liệu cũ.
    ma_lh = models.OneToOneField(
        'bookings.LichHen',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='dich_vu_da_su_dung',
        verbose_name='Lịch hẹn liên kết',
    )

    # Cu: 1 khach mot lan su dung. Moi: so khach cua cung luot ghi nhan.
    so_luong_khach = models.PositiveSmallIntegerField(default=1, verbose_name='So luong khach su dung')
    # Snapshot diem thuc te; du lieu cu chua co snapshot duoc giu null.
    diem_da_cong = models.PositiveIntegerField(null=True, blank=True, verbose_name='Diem da cong thuc te')

    # Luu snapshot gia tai thoi diem ghi nhan, khong tinh lai theo hang moi.
    ma_ctud = models.ForeignKey(
        'notifications.ChuongTrinhUuDai', on_delete=models.PROTECT,
        null=True, blank=True, related_name='dich_vu_da_ap_dung',
        verbose_name='Chuong trinh uu dai da ap dung',
    )
    gia_goc = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='Gia goc luc ghi nhan',
    )
    gia_sau_giam = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='Thanh tien sau tat ca uu dai',
    )
    ty_le_giam_ap_dung = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name='Phan tram giam theo hang luc ghi nhan',
    )

    def __str__(self):
        return f"{self.ma_kh} - {self.ma_dv}"
