from django.conf import settings
from django.db import models


class TaiKhoan(models.Model):
    ma_tk = models.CharField(max_length=10, primary_key=True, verbose_name="Mã tài khoản")
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="thong_tin_tai_khoan",
                                verbose_name="Tài khoản đăng nhập")

    # Đưa số điện thoại và email tập trung hết về bảng TAI_KHOAN ở đây
    so_dien_thoai = models.CharField(max_length=15, unique=True, verbose_name="Số điện thoại")

    vai_tro = models.CharField(max_length=20, choices=[("Khách hàng", "Khách hàng"), ("Nhân viên", "Nhân viên"),
                                                       ("Quản trị viên", "Quản trị viên")], verbose_name="Vai trò")
    ngay_tao = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    ngay_cap_nhat = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")

    def __str__(self):
        return f"{self.user.username} - {self.vai_tro}"

    class Meta:
        db_table = "TAI_KHOAN"
        verbose_name = "Tài khoản"
        verbose_name_plural = "Quản lý tài khoản"


class NhanVien(models.Model):
    ma_nv = models.CharField(max_length=20, primary_key=True, verbose_name="Mã nhân viên")
    ma_tk = models.OneToOneField(TaiKhoan, on_delete=models.PROTECT, related_name="ho_so_nhan_vien",
                                 verbose_name="Tài khoản")
    ho_ten = models.CharField(max_length=100, verbose_name="Họ tên nhân viên")
    gioi_tinh = models.CharField(max_length=10, choices=[("Nam", "Nam"), ("Nữ", "Nữ"), ("Khác", "Khác")],
                                 verbose_name="Giới tính")
    ngay_sinh = models.DateField(verbose_name="Ngày sinh")
    vi_tri = models.CharField(max_length=50, verbose_name="Vị trí công việc")

    # Đã lược bỏ sdt và email ở đây vì đã nằm ở TaiKhoan rồi!

    def __str__(self):
        return self.ho_ten

    class Meta:
        db_table = "NHAN_VIEN"
        verbose_name = "Nhân viên"
        verbose_name_plural = "Quản lý nhân viên"


class LichSuTaiKhoan(models.Model):
    ma_ls = models.CharField(max_length=10, primary_key=True, verbose_name="Mã lịch sử")
    ma_tk = models.ForeignKey(TaiKhoan, on_delete=models.PROTECT, related_name="lich_su_bi_tac_dong",
                              verbose_name="Tài khoản bị tác động")
    ma_tk_thuc_hien = models.ForeignKey(TaiKhoan, on_delete=models.PROTECT, related_name="lich_su_thao_tac",
                                        verbose_name="Người thực hiện")
    hanh_dong = models.CharField(max_length=20, choices=[("Khóa", "Khóa"), ("Mở khóa", "Mở khóa")],
                                 verbose_name="Hành động")
    ly_do = models.TextField(verbose_name="Lý do")
    thoi_gian = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian")

    def __str__(self):
        return f"{self.hanh_dong} - {self.ma_tk}"

    class Meta:
        db_table = "LICH_SU_TAI_KHOAN"
        verbose_name = "Lịch sử tài khoản"
        verbose_name_plural = "Lịch sử tài khoản"
        ordering = ["-thoi_gian"]

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
@receiver(post_save, sender=User)
def dong_bo_tai_khoan_va_vai_tro(sender, instance, created, **kwargs):
    """
    Tự động đồng bộ bản ghi TAI_KHOAN mỗi khi User được tạo mới hoặc cập nhật.
    - Nếu tạo từ DangKyForm: lấy số điện thoại truyền qua thuộc tính `_so_dien_thoai_dang_ky`.
    - Nếu tạo từ Django Admin/createsuperuser: tạo số điện thoại tạm thời duy nhất, tránh vi phạm UNIQUE.
    - Nếu cập nhật User: đồng bộ vai trò theo cờ `is_superuser` và `is_staff`.
    """
    if instance.is_superuser:
        vai_tro_moi = "Quản trị viên"
    elif instance.is_staff:
        vai_tro_moi = "Nhân viên CSKH"
    else:
        vai_tro_moi = "Khách hàng"

    if created:
        if not TaiKhoan.objects.filter(user=instance).exists():
            # Kiểm tra xem có số điện thoại được truyền kèm từ form đăng ký không
            sdt_kem_theo = getattr(instance, '_so_dien_thoai_dang_ky', '').strip()
            if not sdt_kem_theo:
                # Nếu tạo từ Admin không có SĐT, sinh giá trị tạm thời duy nhất để không vi phạm ràng buộc UNIQUE
                prefix = "NV" if (instance.is_staff or instance.is_superuser) else "KH"
                sdt_kem_theo = f"{prefix}_{instance.id:06d}"

            ma_tk_moi = f"TK{instance.id:03d}"
            TaiKhoan.objects.create(
                ma_tk=ma_tk_moi,
                user=instance,
                vai_tro=vai_tro_moi,
                so_dien_thoai=sdt_kem_theo
            )
    else:
        TaiKhoan.objects.filter(user=instance).update(vai_tro=vai_tro_moi)