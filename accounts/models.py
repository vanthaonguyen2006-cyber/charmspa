# accounts/models.py
from django.db import models


class TaiKhoan(models.Model):
    ma_tk = models.CharField(max_length=10, primary_key=True, verbose_name="Mã tài khoản")
    username = models.CharField(max_length=50, unique=True, verbose_name="Tên đăng nhập", null=True, blank=True)  # Thêm trường username
    email = models.EmailField(max_length=100, unique=True, verbose_name="Email đăng nhập")
    so_dien_thoai = models.CharField(max_length=15, unique=True, verbose_name="Số điện thoại")
    mat_khau = models.CharField(max_length=255, verbose_name="Mật khẩu")
    vai_tro = models.CharField(
        max_length=20,
        choices=[('Khách hàng', 'Khách hàng'), ('Nhân viên', 'Nhân viên'), ('Quản trị viên', 'Quản trị viên')],
        verbose_name="Vai trò"
    )
    trang_thai = models.CharField(
        max_length=20,
        default='Hoạt động',
        choices=[('Hoạt động', 'Hoạt động'), ('Đã khóa', 'Đã khóa')],
        verbose_name="Trạng thái"
    )
    ngay_tao = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    ngay_cap_nhat = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")

    def __str__(self):
        return f"{self.email} - {self.vai_tro}"


class NhanVien(models.Model):
    ma_nv = models.CharField(max_length=20, primary_key=True, verbose_name="Mã nhân viên")
    ma_tk = models.ForeignKey(TaiKhoan, on_delete=models.CASCADE, verbose_name="Mã tài khoản")
    ho_ten = models.CharField(max_length=100, verbose_name="Họ tên nhân viên")
    gioi_tinh = models.CharField(
        max_length=10,
        choices=[('Nam', 'Nam'), ('Nữ', 'Nữ'), ('Khác', 'Khác')],
        verbose_name="Giới tính"
    )
    ngay_sinh = models.DateField(verbose_name="Ngày sinh")
    sdt = models.CharField(max_length=15, unique=True, verbose_name="Số điện thoại")
    email = models.EmailField(max_length=100, unique=True, verbose_name="Email")
    vi_tri = models.CharField(max_length=50, verbose_name="Vị trí công việc")

    def __str__(self):
        return self.ho_ten


class LichSuTaiKhoan(models.Model):
    ma_ls = models.CharField(max_length=10, primary_key=True, verbose_name="Mã lịch sử")
    ma_tk = models.ForeignKey(TaiKhoan, on_delete=models.CASCADE, related_name='tai_khoan_bi_tac_dong',
                              verbose_name="Tài khoản bị tác động")
    ma_tk_thuc_hien = models.ForeignKey(TaiKhoan, on_delete=models.CASCADE, related_name='tai_khoan_thao_tac',
                                        verbose_name="Người thực hiện")
    hanh_dong = models.CharField(max_length=20, choices=[('Khóa', 'Khóa'), ('Mở khóa', 'Mở khóa')],
                                 verbose_name="Hành động")
    ly_do = models.TextField(verbose_name="Lý do")
    thoi_gian = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian")

    def __str__(self):
        return f"{self.hanh_dong} - {self.ma_tk}"


from django.db import models

# Create your models here.
