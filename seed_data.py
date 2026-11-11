import os
import random
from datetime import timedelta
import django

# 1. Khởi tạo môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'charmspa.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from accounts.models import NhanVien, TaiKhoan
from bookings.models import LichHen, NgayHoatDong
from customers.models import HangThanhVien, KhachHang
from services.models import DichVu, DichVuDaSuDung

now = timezone.now()
today = now.date()

print("==========================================")
print("   BẮT ĐẦU KÍCH HOẠT NẠP DỮ LIỆU TEST    ")
print("==========================================")

# 2. Lấy hoặc tạo Khách hàng
khach_hang = KhachHang.objects.first()
if not khach_hang:
  user_kh, _ = User.objects.get_or_create(
      username="khach_test", defaults={"email": "khach@test.com"}
  )
  hang_tv, _ = HangThanhVien.objects.get_or_create(
      ma_tv="TV_GOLD",
      defaults={
          "ten_hang": "Vàng",
          "diem_toi_thieu": 100,
          "ty_le_giam_gia": 10.00,
      },
  )
  tk_kh, _ = TaiKhoan.objects.get_or_create(
      user=user_kh,
      defaults={
          "ma_tk": "TK_KH_TEST",
          "so_dien_thoai": "0988777666",
          "vai_tro": "Khách hàng",
      },
  )
  khach_hang, _ = KhachHang.objects.get_or_create(
      ma_kh="KH_TEST",
      defaults={
          "ma_tk": tk_kh,
          "ma_tv": hang_tv,
          "ho_ten": "Trần Thị Minh Anh",
          "gioi_tinh": "Nữ",
      },
  )

print(
    f"[+] Khách hàng sử dụng test: {khach_hang.ho_ten} (Mã: {khach_hang.ma_kh})"
)

# 3. Lấy hoặc tạo Nhân viên
nhan_vien = NhanVien.objects.first()
if not nhan_vien:
  user_nv, _ = User.objects.get_or_create(
      username="nv_test", defaults={"email": "nv@test.com"}
  )
  tk_nv, _ = TaiKhoan.objects.get_or_create(
      user=user_nv,
      defaults={
          "ma_tk": "TK_NV_TEST",
          "so_dien_thoai": "0905123456",
          "vai_tro": "Nhân viên",
      },
  )
  nhan_vien, _ = NhanVien.objects.get_or_create(
      ma_nv="NV_TEST",
      defaults={
          "ma_tk": tk_nv,
          "ho_ten": "Nguyễn Văn Management",
          "chuc_vu": "Quản lý",
      },
  )

print(
    f"[+] Nhân viên sử dụng test: {nhan_vien.ho_ten} (Mã: {nhan_vien.ma_nv})"
)

# 4. Tạo 4 dịch vụ mẫu
dich_vu_data = [
    ("DV01", "Massage Body Đá Nóng", "Massage", 350000),
    ("DV02", "Chăm Sóc Da Mặt Chuyên Sâu", "Chăm sóc da", 500000),
    ("DV03", "Gội Đầu Dưỡng Sinh", "Gội đầu", 200000),
    ("DV04", "Liệu Trình Spa Toàn Thân", "Trị liệu", 800000),
]
dich_vu_list = []
for ma, ten, loai, gia in dich_vu_data:
  dv, _ = DichVu.objects.get_or_create(
      ma_dv=ma,
      defaults={
          "ten_dich_vu": ten,
          "loai_dich_vu": loai,
          "thoi_luong": 60,
          "suc_chua_toi_da": 10,
          "gia_dich_vu": gia,
      },
  )
  dich_vu_list.append(dv)

print(f"[+] Đã chuẩn bị {len(dich_vu_list)} dịch vụ mẫu.")

# 5. Tạo dữ liệu Lịch hẹn & Dịch vụ đã sử dụng cho 7 ngày gần nhất
count_lh = 0
count_sd = 0

for i in range(6, -1, -1):
  day = today - timedelta(days=i)

  # Tạo ngày hoạt động
  ngay_hd, _ = NgayHoatDong.objects.get_or_create(
      ngay=day,
      defaults={
          "ma_nhd": f'NHD-{day.strftime("%Y%m%d")}',
          "trang_thai": "Mở",
      },
  )

  # A. Tạo Lịch hẹn (LichHen)
  num_lh = random.randint(3, 5)
  for j in range(num_lh):
    ma_lh = f"LH-{day.strftime('%m%d')}-{j+1}"
    trang_thai = "CHO_DUYET" if (day == today and j < 2) else "Đã xác nhận"

    _, created = LichHen.objects.get_or_create(
        ma_lh=ma_lh,
        defaults={
            "ma_kh": khach_hang,
            "ma_dv": random.choice(dich_vu_list),
            "ma_nhd": ngay_hd,
            "ngay_hen": day,
            "gio_hen": f"{9 + j*2}:00",
            "so_luong_khach": random.randint(1, 2),
            "trang_thai": trang_thai,
        },
    )
    if created:
      count_lh += 1

  # B. Tạo Dịch vụ đã sử dụng (DichVuDaSuDung)
  num_sd = random.randint(4, 7)
  for k in range(num_sd):
    ma_sd = f"SD-{day.strftime('%m%d')}-{k+1}-{random.randint(10,99)}"
    sd, created = DichVuDaSuDung.objects.get_or_create(
        ma_sd=ma_sd,
        defaults={
            "ma_kh": khach_hang,
            "ma_nv": nhan_vien,
            "ma_dv": random.choice(dich_vu_list),
        },
    )
    if created:
      count_sd += 1

    # Đã sửa: cộng timedelta trực tiếp vào đối tượng datetime của combine()
    dt = timezone.make_aware(
        timezone.datetime.combine(day, timezone.datetime.min.time())
        + timedelta(hours=9 + k)
    )
    DichVuDaSuDung.objects.filter(pk=sd.pk).update(ngay_su_dung=dt)

print(f"[+] Đã nạp thành công {count_lh} Lịch hẹn cho 7 ngày qua.")
print(f"[+] Đã nạp thành công {count_sd} lượt Dịch vụ đã sử dụng.")

print("==========================================")
print(" SUCCESS: ĐÃ NẠP DỮ LIỆU HOÀN TẤT!")
print("==========================================")