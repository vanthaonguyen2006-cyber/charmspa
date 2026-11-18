"""
Tra cứu hồ sơ gắn với người đăng nhập theo cấu trúc hiện tại của nhóm:

    User  ->  TaiKhoan   (related_name = 'thong_tin_tai_khoan')
              TaiKhoan   ->  KhachHang  (related_name = 'ho_so_khach_hang')
              TaiKhoan   ->  NhanVien   (related_name = 'ho_so_nhan_vien')
"""
from accounts.models import (
    ROLE_MANAGER,
    ROLE_STAFF,
    ROLE_CUSTOMER,
    is_manager_role,
    is_staff_role,
    is_staff_portal_user,
    is_customer_role,
)
from . import chat_logic


def first_attr(obj, *names):
    """Giá trị chuỗi không rỗng đầu tiên trong các thuộc tính của obj."""
    if obj is None:
        return ''
    for name in names:
        value = getattr(obj, name, None)
        if value:
            return str(value).strip()
    return ''


def get_taikhoan(user):
    if not getattr(user, 'is_authenticated', False):
        return None
    return getattr(user, 'thong_tin_tai_khoan', None)


def get_khach_hang(user):
    tk = get_taikhoan(user)
    return getattr(tk, 'ho_so_khach_hang', None) if tk is not None else None


def get_nhan_vien(user):
    tk = get_taikhoan(user)
    return getattr(tk, 'ho_so_nhan_vien', None) if tk is not None else None


def customer_contact(user):
    """
    Thông tin khách đã đăng nhập: {fullname, phone, email}.
    Trả về None nếu chưa đăng nhập hoặc tài khoản không có hồ sơ khách hàng (coi như khách vãng lai).
    """
    kh = get_khach_hang(user)
    if kh is None:
        return None
    tk = get_taikhoan(user)
    phone = first_attr(tk, 'so_dien_thoai')
    if not chat_logic.PHONE_RE.match(phone):
        phone = ''
    full_name = getattr(user, 'get_full_name', lambda: '')() or ''
    return {
        'fullname': first_attr(kh, 'ho_ten') or full_name.strip() or user.get_username(),
        'phone': phone,
        'email': (getattr(user, 'email', '') or '').strip(),
    }


def staff_display_name(user, nhan_vien=None):
    nv = nhan_vien if nhan_vien is not None else get_nhan_vien(user)
    full_name = getattr(user, 'get_full_name', lambda: '')() or ''
    return first_attr(nv, 'ho_ten') or full_name.strip() or user.get_username()


ADMIN_ROLES = (ROLE_MANAGER, 'Quản trị viên', 'Admin', 'admin')
ADMIN_ROLE = ROLE_MANAGER


def is_admin(user):
    """Chỉ Quản lý (TaiKhoan.vai_tro == 'Quản lý') hoặc Superuser được sửa kịch bản chatbot."""
    if not getattr(user, 'is_authenticated', False):
        return False
    return bool(user.is_superuser or is_manager_role(user))


def is_staff_user(user):
    """Nhân viên, Quản lý (is_staff_portal_user) hoặc Superuser được vào Quản lý hội thoại."""
    if not getattr(user, 'is_authenticated', False):
        return False
    return bool(user.is_superuser or is_staff_portal_user(user))


def is_staff_or_admin(user):
    return is_staff_user(user)