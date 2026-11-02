"""
Tra cứu hồ sơ gắn với người đăng nhập theo cấu trúc hiện tại của nhóm:

    User  ->  TaiKhoan   (related_name = 'thong_tin_tai_khoan')
              TaiKhoan   ->  KhachHang  (related_name = 'ho_so_khach_hang')
              TaiKhoan   ->  NhanVien   (related_name = 'ho_so_nhan_vien')

Dùng getattr (không import model của app khác) nên module chatbot không phụ thuộc chặt vào
accounts / customers; nếu hồ sơ không tồn tại thì trả về None thay vì báo lỗi.
"""
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


def is_staff_user(user):
    """Nhân viên / quản trị viên (cờ chuẩn của Django, cũng là cờ trang đăng nhập dùng để điều hướng)."""
    return bool(getattr(user, 'is_authenticated', False) and (user.is_staff or user.is_superuser))


def customer_contact(user):
    """
    Thông tin khách đã đăng nhập: {fullname, phone, email}.
    Trả về None nếu chưa đăng nhập hoặc tài khoản không có hồ sơ khách hàng (coi như khách vãng lai).
    """
    kh = get_khach_hang(user)
    if kh is None:
        return None
    tk = get_taikhoan(user)
    # Tài khoản tạo từ trang quản trị có thể mang số điện thoại tạm (ví dụ KH_000012): bỏ qua nếu không phải số điện thoại
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
