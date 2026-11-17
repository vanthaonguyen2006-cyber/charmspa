from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


# =========================================================================
# HỆ THỐNG VAI TRÒ NGHIỆP VỤ WEBSITE (nguồn duy nhất: TaiKhoan.vai_tro)
# Website chỉ có đúng 3 vai trò nghiệp vụ: Quản lý, Nhân viên, Khách hàng.
# Tài khoản Admin kỹ thuật (is_staff=True, is_superuser=True) là tài khoản
# kỹ thuật riêng của Django, chỉ dùng cho /admin/, không phải vai trò nghiệp vụ.
# =========================================================================
ROLE_MANAGER = "Quản lý"
ROLE_STAFF = "Nhân viên"
ROLE_CUSTOMER = "Khách hàng"

ROLE_CHOICES = [
    (ROLE_CUSTOMER, ROLE_CUSTOMER),
    (ROLE_STAFF, ROLE_STAFF),
    (ROLE_MANAGER, ROLE_MANAGER),
]

# Bảng chuyển đổi dữ liệu vai trò cũ của tài khoản nghiệp vụ -> 3 vai trò mới
LEGACY_ROLE_ALIASES = {
    "Admin": ROLE_MANAGER,
    "Nhân viên CSKH": ROLE_STAFF,
    "Chuyên viên": ROLE_STAFF,
}

# Hai vai trò duy nhất được phép phân quyền qua lại tại trang quản lý tài khoản
ASSIGNABLE_ROLES = (ROLE_STAFF, ROLE_MANAGER)


class TaiKhoan(models.Model):
    ma_tk = models.CharField(max_length=10, primary_key=True, verbose_name="Mã tài khoản")
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="thong_tin_tai_khoan",
                                verbose_name="Tài khoản đăng nhập")

    # Đưa số điện thoại và email tập trung hết về bảng TAI_KHOAN ở đây
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

    # Đã lược bỏ sdt, email và trường chức vụ riêng ở đây!

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


# =========================================================================
# HÀM KIỂM TRA QUYỀN DÙNG CHUNG
# - Quyền nghiệp vụ website chỉ dựa vào TaiKhoan.vai_tro (Quản lý / Nhân viên / Khách hàng).
# - Admin kỹ thuật (user.is_superuser and user.is_staff) chỉ được vào /admin/,
#   không thuộc 3 vai trò nghiệp vụ và được loại khỏi danh sách/quản lý website.
# =========================================================================
def normalize_role(value):
    """Chuẩn hóa tên vai trò nghiệp vụ (kể cả tên cũ). Trả về None nếu không nhận diện được."""
    value = (value or "").strip()
    value = LEGACY_ROLE_ALIASES.get(value, value)
    return value if value in dict(ROLE_CHOICES) else None


def get_user_role(user):
    """
    Lấy vai trò nghiệp vụ của user trên website:
    - Trả về None nếu chưa đăng nhập hoặc là Admin kỹ thuật (user.is_superuser).
    - Ngược lại trả về một trong 3 vai trò: Quản lý, Nhân viên, Khách hàng.
    """
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
    """Chỉ vai trò Quản lý được truy cập trang quản lý tài khoản và phân quyền trên website."""
    return get_user_role(user) == ROLE_MANAGER


def is_staff_portal_user(user):
    """Quản lý và Nhân viên được truy cập các trang nghiệp vụ nội bộ."""
    return get_user_role(user) in (ROLE_MANAGER, ROLE_STAFF)


def is_customer_role(user):
    return get_user_role(user) == ROLE_CUSTOMER


def can_access_django_admin(user):
    """
    Chỉ tài khoản Admin kỹ thuật đang hoạt động (is_active=True, is_staff=True, is_superuser=True)
    được truy cập Django Admin tại /admin/.
    Quản lý, Nhân viên và Khách hàng tuyệt đối không được vào /admin/.
    """
    return bool(
        user is not None
        and getattr(user, "is_authenticated", False)
        and user.is_active
        and user.is_staff
        and user.is_superuser
    )


def sync_user_flags_with_role(user, role=None):
    """
    Đồng bộ hai cờ Django cho tài khoản nghiệp vụ:
    - Bảo vệ tuyệt đối tài khoản Admin kỹ thuật (user.is_superuser): không thay đổi hoặc hạ quyền.
    - Tất cả tài khoản nghiệp vụ (Quản lý, Nhân viên, Khách hàng) đều có is_staff=False, is_superuser=False.
    - Không thay đổi is_active.
    """
    if user is None or user.is_superuser:
        return False
    if not user.is_staff and not user.is_superuser:
        return False
    user.is_staff = False
    user.is_superuser = False
    type(user).objects.filter(pk=user.pk).update(is_staff=False, is_superuser=False)
    return True


def dong_bo_vai_tro_tai_khoan_hien_co(ap_dung=False):
    """
    Kiểm tra và chuẩn hóa dữ liệu vai trò + cờ is_staff/is_superuser cho các tài khoản nghiệp vụ hiện có:
    - Bỏ qua và giữ nguyên hoàn toàn tài khoản Admin kỹ thuật (user.is_superuser=True).
    - Chuyển các tài khoản nghiệp vụ có vai trò cũ sang 3 vai trò mới.
    - Không tự ý thay đổi những vai trò không xác định được.
    - Không thay đổi is_active.
    - Mặc định ap_dung=False (chỉ báo cáo, không ghi vào database).
    """
    ket_qua = {
        "admin_ky_thuat_giu_nguyen": [],
        "doi_vai_tro": [],
        "doi_co": [],
        "khong_xac_dinh": [],
    }

    for tk in TaiKhoan.objects.select_related("user"):
        user = tk.user
        if user.is_superuser:
            ket_qua["admin_ky_thuat_giu_nguyen"].append((tk.ma_tk, user.username, tk.vai_tro))
            continue

        vai_tro_chuan = normalize_role(tk.vai_tro)
        if vai_tro_chuan is None:
            ket_qua["khong_xac_dinh"].append((tk.ma_tk, user.username, tk.vai_tro))
            continue

        if vai_tro_chuan != tk.vai_tro:
            ket_qua["doi_vai_tro"].append((tk.ma_tk, user.username, tk.vai_tro, vai_tro_chuan))
            if ap_dung:
                TaiKhoan.objects.filter(pk=tk.pk).update(vai_tro=vai_tro_chuan)

        if user.is_staff or user.is_superuser:
            ket_qua["doi_co"].append((
                tk.ma_tk,
                user.username,
                vai_tro_chuan,
                (user.is_staff, user.is_superuser),
                (False, False),
            ))
            if ap_dung:
                type(user).objects.filter(pk=user.pk).update(is_staff=False, is_superuser=False)

    return ket_qua


@receiver(post_save, sender=User)
def dong_bo_tai_khoan_va_vai_tro(sender, instance, created, **kwargs):
    """
    Tự động tạo bản ghi TAI_KHOAN khi User nghiệp vụ MỚI được tạo.
    - KHÔNG tạo TAI_KHOAN, NhanVien hoặc KhachHang cho Admin kỹ thuật (instance.is_superuser=True).
    - KHÔNG tự động ghi đè TaiKhoan.vai_tro khi cập nhật User.
    """
    if not created:
        return
    if instance.is_superuser:
        return
    if TaiKhoan.objects.filter(user=instance).exists():
        return

    vai_tro_moi = normalize_role(getattr(instance, "_vai_tro_dong_bo", None)) or ROLE_CUSTOMER

    sdt_kem_theo = (getattr(instance, "_so_dien_thoai_dang_ky", "") or "").strip()
    if not sdt_kem_theo:
        prefix = "KH" if vai_tro_moi == ROLE_CUSTOMER else "NV"
        sdt_kem_theo = f"{prefix}_{instance.id:06d}"

    TaiKhoan.objects.create(
        ma_tk=f"TK{instance.id:03d}",
        user=instance,
        vai_tro=vai_tro_moi,
        so_dien_thoai=sdt_kem_theo,
    )
    sync_user_flags_with_role(instance, vai_tro_moi)
