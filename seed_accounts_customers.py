# -*- coding: utf-8 -*-
"""
Script bổ sung dữ liệu thực tế cho app accounts và customers trong Charm Spa Grand.
Thực thi qua: python manage.py shell
Bảo đảm tính toàn vẹn dữ liệu, quan hệ khóa ngoại và khả năng chạy lại (idempotent).
Vị trí trong bảng Nhân viên đồng bộ tuyệt đối với 3 vai trò:
  - Quản trị viên
  - Chuyên viên
  - Nhân viên CSKH
Điểm tích lũy của khách hàng được khởi tạo về 0 và gán hạng Đồng khởi đầu.
"""

import os
import django
from datetime import date, timedelta
from decimal import Decimal

# Khởi tạo Django nếu chạy độc lập
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'charmspa.settings')
django.setup()

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from accounts.models import TaiKhoan, NhanVien, LichSuTaiKhoan
from customers.models import HangThanhVien, KhachHang
from services.models import DichVu, DichVuDaSuDung

DEFAULT_PASSWORD = 'CharmSpa@2026'


def get_next_customer_code():
    """Sinh mã khách hàng dạng KH-00001, KH-00002... dựa trên mã lớn nhất hiện có."""
    max_num = 0
    for kh in KhachHang.objects.filter(ma_kh__startswith='KH-').only('ma_kh'):
        try:
            num = int(kh.ma_kh.split('-')[-1])
            if num > max_num:
                max_num = num
        except (ValueError, IndexError):
            continue
    return f"KH-{max_num + 1:05d}"


def get_next_history_code():
    """Sinh mã lịch sử dạng LS001, LS002..."""
    count_ls = LichSuTaiKhoan.objects.count() + 1
    code = f"LS{count_ls:03d}"
    while LichSuTaiKhoan.objects.filter(ma_ls=code).exists():
        count_ls += 1
        code = f"LS{count_ls:03d}"
    return code


@transaction.atomic
def run_seed():
    print("=================================================================")
    print("   BẮT ĐẦU BỔ SUNG DỮ LIỆU APP ACCOUNTS & CUSTOMERS (CHARM SPA)  ")
    print("=================================================================")

    # 1. Kiểm tra bảng Hạng Thành Viên
    hang_mac_dinh = HangThanhVien.objects.order_by('diem_toi_thieu', 'ma_tv').first()
    if not hang_mac_dinh:
        print("[!] Không tìm thấy dữ liệu Hạng Thành Viên trong CSDL. Tạo các hạng mặc định...")
        hang_dong, _ = HangThanhVien.objects.get_or_create(
            ma_tv="TV_DONG",
            defaults={"ten_hang": "Đồng", "diem_toi_thieu": 0, "diem_toi_da": 999, "ty_le_giam_gia": Decimal("0.00"), "mo_ta_uu_dai": "Hạng khởi đầu dành cho khách hàng mới"}
        )
        hang_bac, _ = HangThanhVien.objects.get_or_create(
            ma_tv="TV_BAC",
            defaults={"ten_hang": "Bạc", "diem_toi_thieu": 1000, "diem_toi_da": 2999, "ty_le_giam_gia": Decimal("5.00"), "mo_ta_uu_dai": "Giảm 5% cho tất cả dịch vụ"}
        )
        hang_vang, _ = HangThanhVien.objects.get_or_create(
            ma_tv="TV_VANG",
            defaults={"ten_hang": "Vàng", "diem_toi_thieu": 3000, "diem_toi_da": 5999, "ty_le_giam_gia": Decimal("10.00"), "mo_ta_uu_dai": "Giảm 10% dịch vụ và ưu tiên đặt lịch"}
        )
        hang_kc, _ = HangThanhVien.objects.get_or_create(
            ma_tv="TV_KIMCUONG",
            defaults={"ten_hang": "Kim Cương", "diem_toi_thieu": 6000, "diem_toi_da": None, "ty_le_giam_gia": Decimal("15.00"), "mo_ta_uu_dai": "Giảm 15% cùng phòng VIP riêng biệt"}
        )
        hang_mac_dinh = hang_dong

    print(f"[*] Hạng thành viên thấp nhất: {hang_mac_dinh.ten_hang} (Mã: {hang_mac_dinh.ma_tv}, Điểm tối thiểu: {hang_mac_dinh.diem_toi_thieu})")

    # 2. Đồng bộ & hoàn thiện hồ sơ cho Superuser hiện tại (TK003 / Nguyen@0203) nếu chưa có hồ sơ nhân viên
    admin_users = User.objects.filter(is_superuser=True)
    for superuser in admin_users:
        tk = getattr(superuser, 'thong_tin_tai_khoan', None)
        if not tk:
            tk, _ = TaiKhoan.objects.get_or_create(
                user=superuser,
                defaults={
                    'ma_tk': f"TK{superuser.id:03d}",
                    'so_dien_thoai': f"0935{superuser.id:06d}"[:10],
                    'vai_tro': "Quản trị viên"
                }
            )
        # Tạo hồ sơ NhanVien cho admin nếu chưa có
        if not hasattr(tk, 'ho_so_nhan_vien') or tk.ho_so_nhan_vien is None:
            nv_code = f"NV{superuser.id:03d}"
            NhanVien.objects.create(
                ma_nv=nv_code,
                ma_tk=tk,
                ho_ten="Nguyễn Quản Trị Hệ Thống",
                gioi_tinh="Nam",
                ngay_sinh=date(1990, 3, 2),
                vi_tri="Quản trị viên"
            )
            print(f"[+] Đã hoàn thiện hồ sơ Nhân viên {nv_code} cho Admin hiện có: {superuser.username}")
        else:
            print(f"[*] Admin {superuser.username} đã có hồ sơ Nhân viên: {tk.ho_so_nhan_vien.ho_ten}")

    # 3. Danh sách Nhân viên & Quản trị viên bổ sung
    # Vị trí chỉ gồm 3 vị trí chuẩn: 'Quản trị viên', 'Nhân viên CSKH', 'Chuyên viên'
    staff_data_list = [
        {
            "username": "admin_lanhuong",
            "email": "lanhuong.admin@charmspa.vn",
            "first_name": "Lan Hương",
            "last_name": "Phạm",
            "phone": "0912345678",
            "ho_ten": "Phạm Lan Hương",
            "gioi_tinh": "Nữ",
            "ngay_sinh": date(1992, 5, 15),
            "vai_tro": "Quản trị viên",
            "vi_tri": "Quản trị viên",
            "is_staff": True,
            "is_superuser": True,
        },
        {
            "username": "cskh_minhquan",
            "email": "minhquan.cskh@charmspa.vn",
            "first_name": "Minh Quân",
            "last_name": "Lê",
            "phone": "0913456789",
            "ho_ten": "Lê Minh Quân",
            "gioi_tinh": "Nam",
            "ngay_sinh": date(1996, 8, 20),
            "vai_tro": "Nhân viên CSKH",
            "vi_tri": "Nhân viên CSKH",
            "is_staff": True,
            "is_superuser": False,
        },
        {
            "username": "cskh_thanhha",
            "email": "thanhha.cskh@charmspa.vn",
            "first_name": "Thanh Hà",
            "last_name": "Vũ",
            "phone": "0914567890",
            "ho_ten": "Vũ Thanh Hà",
            "gioi_tinh": "Nữ",
            "ngay_sinh": date(1998, 11, 12),
            "vai_tro": "Nhân viên CSKH",
            "vi_tri": "Nhân viên CSKH",
            "is_staff": True,
            "is_superuser": False,
        },
        {
            "username": "cv_hoanganh",
            "email": "hoanganh.spa@charmspa.vn",
            "first_name": "Ngọc Anh",
            "last_name": "Hoàng",
            "phone": "0915678901",
            "ho_ten": "Hoàng Ngọc Anh",
            "gioi_tinh": "Nữ",
            "ngay_sinh": date(1995, 4, 18),
            "vai_tro": "Chuyên viên",
            "vi_tri": "Chuyên viên",
            "is_staff": True,
            "is_superuser": False,
        },
        {
            "username": "cv_ducthuan",
            "email": "ducthuan.spa@charmspa.vn",
            "first_name": "Đức Thuận",
            "last_name": "Đỗ",
            "phone": "0916789012",
            "ho_ten": "Đỗ Đức Thuận",
            "gioi_tinh": "Nam",
            "ngay_sinh": date(1994, 9, 25),
            "vai_tro": "Chuyên viên",
            "vi_tri": "Chuyên viên",
            "is_staff": True,
            "is_superuser": False,
        },
    ]

    print("\n--- BỔ SUNG TÀI KHOẢN NHÂN VIÊN & QUẢN TRỊ VIÊN ---")
    staff_created_count = 0
    staff_existing_count = 0

    for s in staff_data_list:
        user = User.objects.filter(username=s["username"]).first()
        if not user:
            user = User(
                username=s["username"],
                email=s["email"],
                first_name=s["first_name"],
                last_name=s["last_name"],
                is_staff=s["is_staff"],
                is_superuser=s["is_superuser"],
                is_active=True,
            )
            user._so_dien_thoai_dang_ky = s["phone"]
            user.set_password(DEFAULT_PASSWORD)
            user.save()

            tk = TaiKhoan.objects.get(user=user)
            if tk.vai_tro != s["vai_tro"] or tk.so_dien_thoai != s["phone"]:
                tk.vai_tro = s["vai_tro"]
                tk.so_dien_thoai = s["phone"]
                tk.save(update_fields=['vai_tro', 'so_dien_thoai'])

            ma_nv = f"NV{user.id:03d}"
            NhanVien.objects.create(
                ma_nv=ma_nv,
                ma_tk=tk,
                ho_ten=s["ho_ten"],
                gioi_tinh=s["gioi_tinh"],
                ngay_sinh=s["ngay_sinh"],
                vi_tri=s["vi_tri"]
            )
            staff_created_count += 1
            print(f"[+] Tạo thành công Nhân viên: {s['ho_ten']} ({s['username']}) - {s['vai_tro']} - Mã NV: {ma_nv}")
        else:
            staff_existing_count += 1
            print(f"[*] Tài khoản nhân viên '{s['username']}' đã tồn tại. Giữ nguyên.")

    # 4. Danh sách Khách hàng đa dạng (Tất cả điểm tích lũy khởi tạo về 0, hạng Đồng)
    customers_data_list = [
        {
            "username": "kh_nguyenhoa",
            "email": "nguyenhoa99@gmail.com",
            "first_name": "Quỳnh Hoa",
            "last_name": "Nguyễn Thị",
            "phone": "0903112233",
            "ho_ten": "Nguyễn Thị Quỳnh Hoa",
            "gioi_tinh": "Nữ",
            "ngay_sinh": date(1999, 3, 14),
            "points": 0,
            "target_tier": "TV_DONG",
            "is_active": True,
        },
        {
            "username": "kh_tuananh",
            "email": "tuananh.le88@gmail.com",
            "first_name": "Tuấn Anh",
            "last_name": "Lê",
            "phone": "0903223344",
            "ho_ten": "Lê Tuấn Anh",
            "gioi_tinh": "Nam",
            "ngay_sinh": date(1988, 7, 22),
            "points": 0,
            "target_tier": "TV_DONG",
            "is_active": True,
        },
        {
            "username": "kh_maichi",
            "email": "maichi.dang@gmail.com",
            "first_name": "Mai Chi",
            "last_name": "Đặng",
            "phone": "0903334455",
            "ho_ten": "Đặng Mai Chi",
            "gioi_tinh": "Nữ",
            "ngay_sinh": date(1993, 12, 5),
            "points": 0,
            "target_tier": "TV_DONG",
            "is_active": True,
        },
        {
            "username": "kh_phuongthao",
            "email": "phuongthao.vu@gmail.com",
            "first_name": "Phương Thảo",
            "last_name": "Vũ",
            "phone": "0903445566",
            "ho_ten": "Vũ Phương Thảo",
            "gioi_tinh": "Nữ",
            "ngay_sinh": date(1991, 9, 30),
            "points": 0,
            "target_tier": "TV_DONG",
            "is_active": True,
        },
        {
            "username": "kh_quanghuy",
            "email": "quanghuy.bui@gmail.com",
            "first_name": "Quang Huy",
            "last_name": "Bùi",
            "phone": "0903556677",
            "ho_ten": "Bùi Quang Huy",
            "gioi_tinh": "Nam",
            "ngay_sinh": date(1985, 2, 17),
            "points": 0,
            "target_tier": "TV_DONG",
            "is_active": True,
        },
        {
            "username": "kh_thuytien",
            "email": "thuytien.nguyen@gmail.com",
            "first_name": "Thủy Tiên",
            "last_name": "Nguyễn",
            "phone": "0903667788",
            "ho_ten": "Nguyễn Thủy Tiên",
            "gioi_tinh": "Nữ",
            "ngay_sinh": date(1990, 10, 10),
            "points": 0,
            "target_tier": "TV_DONG",
            "is_active": True,
        },
        {
            "username": "kh_hoangnam",
            "email": "hoangnam.tran@gmail.com",
            "first_name": "Hoàng Nam",
            "last_name": "Trần",
            "phone": "0903778899",
            "ho_ten": "Trần Hoàng Nam",
            "gioi_tinh": "Nam",
            "ngay_sinh": date(1987, 6, 28),
            "points": 0,
            "target_tier": "TV_DONG",
            "is_active": True,
        },
        {
            "username": "kh_baongoc",
            "email": "baongoc.pham@gmail.com",
            "first_name": "Bảo Ngọc",
            "last_name": "Phạm",
            "phone": "0903889900",
            "ho_ten": "Phạm Bảo Ngọc",
            "gioi_tinh": "Nữ",
            "ngay_sinh": date(1986, 4, 12),
            "points": 0,
            "target_tier": "TV_DONG",
            "is_active": True,
        },
        {
            "username": "kh_ducphuc",
            "email": "ducphuc.ngo@gmail.com",
            "first_name": "Đức Phúc",
            "last_name": "Ngô",
            "phone": "0903990011",
            "ho_ten": "Ngô Đức Phúc",
            "gioi_tinh": "Nam",
            "ngay_sinh": date(1982, 1, 25),
            "points": 0,
            "target_tier": "TV_DONG",
            "is_active": True,
        },
        {
            "username": "kh_minhkhanh",
            "email": "minhkhanh.tran@gmail.com",
            "first_name": "Minh Khánh",
            "last_name": "Trần",
            "phone": "0908234567",
            "ho_ten": "Trần Minh Khánh",
            "gioi_tinh": "Khác",
            "ngay_sinh": date(1995, 12, 20),
            "points": 0,
            "target_tier": "TV_DONG",
            "is_active": True,
        },
        {
            "username": "kh_camly",
            "email": "camly.dinh@gmail.com",
            "first_name": "Cẩm Ly",
            "last_name": "Đinh",
            "phone": "0908123456",
            "ho_ten": "Đinh Cẩm Ly",
            "gioi_tinh": "Nữ",
            "ngay_sinh": date(1997, 8, 8),
            "points": 0,
            "target_tier": "TV_DONG",
            "is_active": False,
        },
    ]

    print("\n--- BỔ SUNG HỒ SƠ KHÁCH HÀNG & TÀI KHOẢN ---")
    customer_created_count = 0
    customer_existing_count = 0

    created_customers_dict = {}

    for c in customers_data_list:
        user = User.objects.filter(username=c["username"]).first()
        if not user:
            user = User(
                username=c["username"],
                email=c["email"],
                first_name=c["first_name"],
                last_name=c["last_name"],
                is_staff=False,
                is_superuser=False,
                is_active=c["is_active"],
            )
            user._so_dien_thoai_dang_ky = c["phone"]
            user.set_password(DEFAULT_PASSWORD)
            user.save()

            tk = TaiKhoan.objects.get(user=user)
            if tk.vai_tro != "Khách hàng" or tk.so_dien_thoai != c["phone"]:
                tk.vai_tro = "Khách hàng"
                tk.so_dien_thoai = c["phone"]
                tk.save(update_fields=['vai_tro', 'so_dien_thoai'])

            ma_kh = get_next_customer_code()
            kh = KhachHang.objects.create(
                ma_kh=ma_kh,
                ma_tk=tk,
                ma_tv=hang_mac_dinh,
                ho_ten=c["ho_ten"],
                ngay_sinh=c["ngay_sinh"],
                gioi_tinh=c["gioi_tinh"],
                diem_tich_luy_kh=0
            )
            customer_created_count += 1
            created_customers_dict[c["username"]] = kh
            print(f"[+] Tạo thành công Khách hàng: {c['ho_ten']} ({c['username']}) - Mã KH: {ma_kh} - Hạng: {hang_mac_dinh.ten_hang} - Điểm: 0 - Trạng thái: {'Hoạt động' if c['is_active'] else 'Đã khóa'}")
        else:
            customer_existing_count += 1
            kh = KhachHang.objects.filter(ma_tk__user=user).first()
            if kh:
                created_customers_dict[c["username"]] = kh
            print(f"[*] Tài khoản khách hàng '{c['username']}' đã tồn tại. Giữ nguyên.")

    # 5. Bổ sung Lịch sử Tài khoản (LichSuTaiKhoan)
    print("\n--- BỔ SUNG LỊCH SỬ KHÓA / MỞ KHÓA TÀI KHOẢN ---")
    admin_tk = TaiKhoan.objects.filter(user__is_superuser=True).first()
    cskh_tk = TaiKhoan.objects.filter(vai_tro="Nhân viên CSKH").first() or admin_tk

    history_created_count = 0

    camly_kh = created_customers_dict.get("kh_camly")
    if camly_kh and camly_kh.ma_tk:
        if not LichSuTaiKhoan.objects.filter(ma_tk=camly_kh.ma_tk, hanh_dong="Khóa").exists():
            ma_ls = get_next_history_code()
            LichSuTaiKhoan.objects.create(
                ma_ls=ma_ls,
                ma_tk=camly_kh.ma_tk,
                ma_tk_thuc_hien=admin_tk,
                hanh_dong="Khóa",
                ly_do="Khách hàng gửi yêu cầu qua email xin tạm khóa tài khoản để bảo mật trong thời gian công tác nước ngoài."
            )
            history_created_count += 1
            print(f"[+] Tạo bản ghi Lịch sử {ma_ls}: Khóa tài khoản cho {camly_kh.ho_ten}")

    tuananh_kh = created_customers_dict.get("kh_tuananh")
    if tuananh_kh and tuananh_kh.ma_tk:
        if not LichSuTaiKhoan.objects.filter(ma_tk=tuananh_kh.ma_tk).exists():
            ls1 = get_next_history_code()
            LichSuTaiKhoan.objects.create(
                ma_ls=ls1,
                ma_tk=tuananh_kh.ma_tk,
                ma_tk_thuc_hien=admin_tk,
                hanh_dong="Khóa",
                ly_do="Tạm khóa bảo vệ do phát hiện đăng nhập sai mật khẩu liên tiếp 5 lần."
            )
            history_created_count += 1

            ls2 = get_next_history_code()
            LichSuTaiKhoan.objects.create(
                ma_ls=ls2,
                ma_tk=tuananh_kh.ma_tk,
                ma_tk_thuc_hien=cskh_tk,
                hanh_dong="Mở khóa",
                ly_do="Khách hàng đã gọi đến hotline hỗ trợ, xác minh danh tính và CCCD thành công. Mở khóa tài khoản."
            )
            history_created_count += 1
            print(f"[+] Tạo bản ghi Lịch sử {ls1} & {ls2}: Khóa & Mở khóa tài khoản cho {tuananh_kh.ho_ten}")

    print("\n=================================================================")
    print("                      TỔNG KẾT NẠP DỮ LIỆU                      ")
    print("=================================================================")
    print(f" Nhân viên & Admin mới tạo:  {staff_created_count} (Đã có sẵn: {staff_existing_count})")
    print(f" Khách hàng mới tạo:          {customer_created_count} (Đã có sẵn: {customer_existing_count})")
    print(f" Lịch sử tài khoản tạo mới:  {history_created_count}")
    print(f" Mật khẩu mặc định tài khoản: {DEFAULT_PASSWORD}")
    print("=================================================================\n")


if __name__ == '__main__':
    run_seed()
