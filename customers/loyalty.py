
from django.db import transaction

from customers.models import (
    KhachHang,
    HangThanhVien,
    LichSuTichDiemBooking,
)

from bookings.models import LichHen


def cong_diem_khi_hoan_thanh(ma_lh):
    """
    Cộng điểm cố định theo dịch vụ khi lịch hẹn Hoàn thành.

    - Không phụ thuộc giá gốc hay giá ưu đãi.
    - Mỗi lịch chỉ được cộng điểm một lần.
    - Tự động kiểm tra hạng thành viên.
    - Không cộng điểm cho lịch chưa hoàn thành.
    """

    with transaction.atomic():

        # 1. Khóa lịch hẹn khi xử lý để tránh cộng điểm trùng.
        lich_hen = (
            LichHen.objects
            .select_for_update()
            .select_related("ma_dv")
            .get(pk=ma_lh)
        )

        # 2. Chỉ cộng khi dịch vụ đã hoàn thành.
        if lich_hen.trang_thai != "Hoàn thành":
            return {
                "success": False,
                "message": "Lịch hẹn chưa hoàn thành.",
                "diem_cong": 0,
            }

        # 3. Kiểm tra lịch này đã cộng điểm chưa.
        if LichSuTichDiemBooking.objects.filter(
            ma_lh=lich_hen
        ).exists():
            return {
                "success": False,
                "message": "Lịch hẹn đã được cộng điểm trước đó.",
                "diem_cong": 0,
            }

        # 4. Khóa hồ sơ khách hàng.
        khach_hang = (
            KhachHang.objects
            .select_for_update()
            .get(pk=lich_hen.ma_kh_id)
        )

        # 5. Tính điểm cố định theo số khách sử dụng dịch vụ.
        diem_moi_khach = int(
            lich_hen.ma_dv.diem_tich_luy_dich_vu or 0
        )

        so_luong_khach = int(lich_hen.so_luong_khach or 1)

        if so_luong_khach < 1:
            raise ValueError("Số lượng khách không hợp lệ.")

        diem_cong = diem_moi_khach * so_luong_khach

        if diem_cong < 0:
            raise ValueError(
                "Điểm tích lũy của dịch vụ không được âm."
            )

        diem_truoc = khach_hang.diem_tich_luy_kh or 0
        diem_sau = diem_truoc + diem_cong

        # 6. Cập nhật tổng điểm của khách.
        khach_hang.diem_tich_luy_kh = diem_sau

        # 7. Xét hạng thành viên theo mốc điểm.
        hang_moi = (
            HangThanhVien.objects
            .filter(diem_toi_thieu__lte=diem_sau)
            .order_by("-diem_toi_thieu")
            .first()
        )

        hang_cu_id = khach_hang.ma_tv_id

        if hang_moi:
            khach_hang.ma_tv = hang_moi

        khach_hang.save(
            update_fields=["diem_tich_luy_kh", "ma_tv"]
        )

        # 8. Lưu lịch sử, chống cộng điểm trùng.
        LichSuTichDiemBooking.objects.create(
            ma_lh=lich_hen,
            ma_kh=khach_hang,
            diem_cong=diem_cong,
            diem_truoc=diem_truoc,
            diem_sau=diem_sau,
        )

        return {
            "success": True,
            "message": "Cộng điểm tích lũy thành công.",
            "diem_cong": diem_cong,
            "diem_truoc": diem_truoc,
            "diem_sau": diem_sau,
            "hang_moi": hang_moi.ten_hang if hang_moi else None,
            "len_hang": (
                hang_moi is not None
                and hang_cu_id != hang_moi.pk
            ),
        }
