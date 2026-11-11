# -*- coding: utf-8 -*-
"""
Script tạo dữ liệu lịch sử dịch vụ (DichVuDaSuDung) thực tế cho khách hàng,
bảo đảm phân bổ chuẩn xác điểm tích lũy và phủ đủ 4 Hạng Thành Viên:
  - Hạng Đồng:      0 - 999 điểm
  - Hạng Bạc:       1.000 - 2.999 điểm
  - Hạng Vàng:      3.000 - 5.999 điểm
  - Hạng Kim Cương: từ 6.000 điểm trở lên
"""

import os
import random
from datetime import datetime, time, timedelta

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'charmspa.settings')
django.setup()

from django.db import transaction
from django.utils import timezone
from accounts.models import NhanVien
from customers.models import HangThanhVien, KhachHang
from services.models import DichVu, DichVuDaSuDung


@transaction.atomic
def run_seed_service_history():
    print("=================================================================")
    print("     TẠO DỮ LIỆU LỊCH SỬ DỊCH VỤ & NÂNG HẠNG 4 HẠNG THÀNH VIÊN   ")
    print("=================================================================")

    # 1. Kiểm tra danh sách Dịch vụ và Chuyên viên
    dich_vu_list = list(DichVu.objects.all().order_by('ma_dv'))
    if not dich_vu_list:
        print("[!] Không tìm thấy dịch vụ nào trong bảng DichVu!")
        return

    print(f"[*] Tìm thấy {len(dich_vu_list)} dịch vụ trong cơ sở dữ liệu.")

    chuyen_vien_list = list(NhanVien.objects.filter(vi_tri="Chuyên viên").order_by('ma_nv'))
    if not chuyen_vien_list:
        chuyen_vien_list = list(NhanVien.objects.all().order_by('ma_nv'))

    print(f"[*] Sử dụng {len(chuyen_vien_list)} chuyên viên thực hiện trị liệu:")
    for cv in chuyen_vien_list:
        print(f"    - {cv.ma_nv}: {cv.ho_ten} ({cv.vi_tri})")

    # 2. Xóa các bản ghi DichVuDaSuDung cũ để tái lập dữ liệu đồng nhất
    deleted_count, _ = DichVuDaSuDung.objects.all().delete()
    print(f"[*] Đã làm sạch {deleted_count} bản ghi lịch sử dịch vụ cũ.")

    # 3. Kế hoạch phân bổ lượt sử dụng dịch vụ cho từng khách hàng
    # Để đạt đủ 4 hạng thành viên:
    # - Hạng Đồng (0 - 999 điểm): KH-00001, KH-00002, KH-00003, KH-00004, KH-00012
    # - Hạng Bạc (1.000 - 2.999 điểm): KH-00005, KH-00006, KH-00011
    # - Hạng Vàng (3.000 - 5.999 điểm): KH-00007, KH-00008
    # - Hạng Kim Cương (>= 6.000 điểm): KH-00009, KH-00010
    customer_service_plan = {
        # KHÁCH HÀNG HẠNG ĐỒNG (0 - 999 điểm)
        "KH-00001": [],  # 0 điểm - Khách hàng mới
        "KH-00002": [],  # 0 điểm - Khách hàng mới
        "KH-00003": ["DV01"],  # 89 điểm
        "KH-00004": ["DV04", "DV09", "DV11"],  # 95 + 85 + 60 = 240 điểm
        "KH-00012": ["DV13"],  # 50 điểm (Khách đã khóa)

        # KHÁCH HÀNG HẠNG BẠC (1.000 - 2.999 điểm)
        "KH-00005": [  # ~1.220 điểm
            "DV01", "DV04", "DV05", "DV07", "DV09", "DV10",
            "DV11", "DV12", "DV13", "DV14", "DV15", "DV16"
        ],
        "KH-00006": [  # ~1.940 điểm (18 lượt dịch vụ)
            "DV01", "DV02", "DV03", "DV04", "DV05", "DV06", "DV07", "DV08",
            "DV09", "DV10", "DV11", "DV12", "DV13", "DV14", "DV15", "DV16",
            "DV03", "DV16"
        ],
        "KH-00011": [  # ~2.560 điểm (24 lượt dịch vụ)
            "DV01", "DV02", "DV03", "DV04", "DV05", "DV06", "DV07", "DV08",
            "DV09", "DV10", "DV11", "DV12", "DV13", "DV14", "DV15", "DV16",
            "DV02", "DV03", "DV06", "DV07", "DV08", "DV12", "DV15", "DV16"
        ],

        # KHÁCH HÀNG HẠNG VÀNG (3.000 - 5.999 điểm)
        "KH-00007": [  # ~3.680 điểm (35 lượt dịch vụ)
            "DV01", "DV02", "DV03", "DV04", "DV05", "DV06", "DV07", "DV08", "DV09", "DV10",
            "DV11", "DV12", "DV13", "DV14", "DV15", "DV16", "DV01", "DV02", "DV03", "DV04",
            "DV05", "DV06", "DV07", "DV08", "DV09", "DV10", "DV11", "DV12", "DV13", "DV14",
            "DV15", "DV16", "DV03", "DV08", "DV16"
        ],
        "KH-00008": [  # ~5.090 điểm (48 lượt dịch vụ)
            "DV01", "DV02", "DV03", "DV04", "DV05", "DV06", "DV07", "DV08", "DV09", "DV10",
            "DV11", "DV12", "DV13", "DV14", "DV15", "DV16", "DV01", "DV02", "DV03", "DV04",
            "DV05", "DV06", "DV07", "DV08", "DV09", "DV10", "DV11", "DV12", "DV13", "DV14",
            "DV15", "DV16", "DV02", "DV03", "DV06", "DV07", "DV08", "DV12", "DV15", "DV16",
            "DV02", "DV03", "DV06", "DV07", "DV08", "DV12", "DV15", "DV16"
        ],

        # KHÁCH HÀNG HẠNG KIM CƯƠNG (>= 6.000 điểm)
        "KH-00009": [  # ~6.720 điểm (63 lượt dịch vụ)
            "DV01", "DV02", "DV03", "DV04", "DV05", "DV06", "DV07", "DV08", "DV09", "DV10",
            "DV11", "DV12", "DV13", "DV14", "DV15", "DV16", "DV01", "DV02", "DV03", "DV04",
            "DV05", "DV06", "DV07", "DV08", "DV09", "DV10", "DV11", "DV12", "DV13", "DV14",
            "DV15", "DV16", "DV01", "DV02", "DV03", "DV04", "DV05", "DV06", "DV07", "DV08",
            "DV09", "DV10", "DV11", "DV12", "DV13", "DV14", "DV15", "DV16", "DV02", "DV03",
            "DV06", "DV07", "DV08", "DV12", "DV15", "DV16", "DV02", "DV03", "DV06", "DV07",
            "DV08", "DV12", "DV16"
        ],
        "KH-00010": [  # ~8.650 điểm (81 lượt dịch vụ)
            "DV01", "DV02", "DV03", "DV04", "DV05", "DV06", "DV07", "DV08", "DV09", "DV10",
            "DV11", "DV12", "DV13", "DV14", "DV15", "DV16", "DV01", "DV02", "DV03", "DV04",
            "DV05", "DV06", "DV07", "DV08", "DV09", "DV10", "DV11", "DV12", "DV13", "DV14",
            "DV15", "DV16", "DV01", "DV02", "DV03", "DV04", "DV05", "DV06", "DV07", "DV08",
            "DV09", "DV10", "DV11", "DV12", "DV13", "DV14", "DV15", "DV16", "DV01", "DV02",
            "DV03", "DV04", "DV05", "DV06", "DV07", "DV08", "DV09", "DV10", "DV11", "DV12",
            "DV13", "DV14", "DV15", "DV16", "DV02", "DV03", "DV06", "DV07", "DV08", "DV12",
            "DV15", "DV16", "DV02", "DV03", "DV06", "DV07", "DV08", "DV12", "DV15", "DV16", "DV16"
        ],
    }

    dich_vu_dict = {dv.ma_dv: dv for dv in dich_vu_list}
    now = timezone.now()

    all_sd_objects = []
    global_sd_idx = 1

    print("\n--- BẮT ĐẦU TẠO LỊCH SỬ DỊCH VỤ CHO TỪNG KHÁCH HÀNG ---")

    for ma_kh, dv_code_list in customer_service_plan.items():
        kh = KhachHang.objects.filter(ma_kh=ma_kh).first()
        if not kh:
            continue

        num_services = len(dv_code_list)
        total_pts = 0

        # Phân bổ ngày trong khoảng 1 -> 90 ngày trước
        for idx, dv_code in enumerate(dv_code_list):
            dv = dich_vu_dict.get(dv_code)
            if not dv:
                continue

            cv = chuyen_vien_list[idx % len(chuyen_vien_list)]
            ma_sd = f"SD{global_sd_idx:04d}"
            global_sd_idx += 1

            # Tính ngày sử dụng dịch vụ trong quá khứ
            days_ago = max(1, int(90 * (1 - (idx / max(1, num_services)))))
            service_dt = now - timedelta(days=days_ago, hours=random.randint(1, 8), minutes=random.randint(0, 59))

            sd = DichVuDaSuDung(
                ma_sd=ma_sd,
                ma_kh=kh,
                ma_nv=cv,
                ma_dv=dv,
                ngay_su_dung=service_dt
            )
            all_sd_objects.append(sd)
            total_pts += (dv.diem_tich_luy_dich_vu or 0)

        # Cập nhật điểm tích lũy và Hạng thành viên tương ứng
        tier = (
            HangThanhVien.objects.filter(diem_toi_thieu__lte=total_pts)
            .order_by('-diem_toi_thieu')
            .first()
        )
        if not tier:
            tier = HangThanhVien.objects.order_by('diem_toi_thieu', 'ma_tv').first()

        kh.diem_tich_luy_kh = total_pts
        kh.ma_tv = tier
        kh.save(update_fields=['diem_tich_luy_kh', 'ma_tv'])

        print(f"[+] {kh.ma_kh} | {kh.ho_ten:<24} -> {num_services:>2} dịch vụ | Tổng điểm: {total_pts:>5} | Hạng: {tier.ten_hang}")

    # 4. Lưu toàn bộ bản ghi dịch vụ đã sử dụng vào CSDL
    DichVuDaSuDung.objects.bulk_create(all_sd_objects)
    print(f"\n[v] Đã lưu thành công tổng cộng {len(all_sd_objects)} bản ghi vào bảng DichVuDaSuDung!")

    # 5. Thống kê kết quả phân bổ 4 hạng thành viên
    print("\n=================================================================")
    print("                THỐNG KÊ PHÂN BỔ 4 HẠNG THÀNH VIÊN               ")
    print("=================================================================")
    for h in HangThanhVien.objects.all().order_by('diem_toi_thieu'):
        count_kh = KhachHang.objects.filter(ma_tv=h).count()
        print(f" Hạng {h.ten_hang:<10} ({h.ma_tv:<11}): {count_kh:>2} khách hàng (Điểm: {h.diem_toi_thieu} -> {h.diem_toi_da or 'Không giới hạn'})")
    print("=================================================================\n")


if __name__ == '__main__':
    run_seed_service_history()
