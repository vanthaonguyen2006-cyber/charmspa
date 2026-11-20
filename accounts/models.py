from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models


ROLE_MANAGER = "Quản lý"
ROLE_STAFF = "Nhân viên"
ROLE_CUSTOMER = "Khách hàng"

ROLE_CHOICES = [
    (ROLE_CUSTOMER, ROLE_CUSTOMER),
    (ROLE_STAFF, ROLE_STAFF),
    (ROLE_MANAGER, ROLE_MANAGER),
]

ASSIGNABLE_ROLES = (ROLE_STAFF, ROLE_MANAGER)


class TaiKhoan(models.Model):
    ma_tk = models.CharField(max_length=10, primary_key=True, verbose_name="Mã tài khoản")
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="thong_tin_tai_khoan",
                                verbose_name="Tài khoản đăng nhập")

    so_dien_thoai = models.CharField(max_length=15, unique=True, verbose_name="Số điện thoại")

    vai_tro = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name="Vai trò")
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

# HÀM KIỂM TRA QUYỀN DÙNG CHUNG

def normalize_role(value):
    """Kiểm tra và trả về tên vai trò hợp lệ trong 3 vai trò nghiệp vụ (Quản lý, Nhân viên, Khách hàng)."""
    value = (value or "").strip()
    return value if value in dict(ROLE_CHOICES) else None


def get_user_role(user):
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    if user.is_superuser:
        return None
    try:
        tai_khoan = user.thong_tin_tai_khoan
    except ObjectDoesNotExist:
        tai_khoan = None

    if tai_khoan is not None:
        return normalize_role(tai_khoan.vai_tro) or ROLE_CUSTOMER

    return ROLE_CUSTOMER


def is_manager_role(user):
    return get_user_role(user) == ROLE_MANAGER


def is_staff_role(user):
    return get_user_role(user) == ROLE_STAFF


def can_manage_accounts(user):
    return get_user_role(user) == ROLE_MANAGER


def is_staff_portal_user(user):
    return get_user_role(user) in (ROLE_MANAGER, ROLE_STAFF)


def is_customer_role(user):
    return get_user_role(user) == ROLE_CUSTOMER


def can_access_django_admin(user):
    return bool(
        user is not None
        and getattr(user, "is_authenticated", False)
        and user.is_active
        and user.is_staff
        and user.is_superuser
    )


def sync_user_flags_with_role(user):
    if user is None or user.is_superuser:
        return False
    if not user.is_staff and not user.is_superuser:
        return False
    user.is_staff = False
    user.is_superuser = False
    type(user).objects.filter(pk=user.pk).update(is_staff=False, is_superuser=False)
    return True
