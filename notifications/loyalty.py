"""Thong bao noi bo cho khach sau khi Booking hoan thanh va duoc cong diem.

Luu file nay tai notifications/loyalty.py.
Khong gui email/SMS; 'Da gui' nghia la thong bao da duoc tao cho khach trong DB.
Ham duoc goi trong transaction.atomic cua booking_staff_complete.
"""
import uuid

from django.db import IntegrityError, transaction
from django.utils import timezone

from notifications.models import ThongBao, ThongBaoKhachHang
from bookings.models import LichHen


def _tao_ma(model, field, prefix):
    """Sinh ma toi da 10 ky tu, khong trung voi du lieu hien tai."""
    for _ in range(20):
        ma = prefix + uuid.uuid4().hex[:8].upper()
        if not model.objects.filter(**{field: ma}).exists():
            return ma
    raise RuntimeError('Khong tao duoc ma thong bao duy nhat.')


def _luu_thong_bao(lich_hen, loai_tb, tieu_de, noi_dung):
    """Mot thong bao moi loai cho mot Booking. Caller phai lock Booking."""
    thong_bao = ThongBao.objects.filter(
        ma_lh=lich_hen,
        loai_tb=loai_tb,
    ).first()
    if thong_bao is not None:
        # Khong gui lai thong bao cu, ke ca khi duoc goi lan nua.
        return False

    tb = ThongBao.objects.create(
        ma_tb=_tao_ma(ThongBao, 'ma_tb', 'TB'),
        ma_lh=lich_hen,
        loai_tb=loai_tb,
        tieu_de=tieu_de,
        noi_dung=noi_dung,
        trang_thai='Đã gửi',
    )
    ThongBaoKhachHang.objects.create(
        ma_tbkh=_tao_ma(ThongBaoKhachHang, 'ma_tbkh', 'TK'),
        ma_tb=tb,
        ma_kh=lich_hen.ma_kh,
        thoi_gian_gui=timezone.now(),
        trang_thai_gui='Đã gửi',
    )
    return True


def tao_thong_bao_tich_diem(ma_lh, ket_qua):
    """Tao thong bao diem va len hang cho Booking vua hoan thanh.

    Goi ben trong transaction.atomic sau cong_diem_khi_hoan_thanh.
    Ham khong cong diem; chi doc ket_qua tu ham loyalty.
    """
    if not ket_qua.get('success'):
        return 0

    # Caller da khoa Booking trong transaction; lay du lieu de tao thong bao.
    lich_hen = LichHen.objects.select_related('ma_kh', 'ma_dv').get(pk=ma_lh)
    if lich_hen.trang_thai != 'Hoàn thành':
        raise ValueError('Khong the thong bao diem cho Booking chua hoan thanh.')

    diem = int(ket_qua.get('diem_cong', 0))
    ten_dv = lich_hen.ma_dv.ten_dich_vu
    so_khach = lich_hen.so_luong_khach or 1
    created = 0

    if _luu_thong_bao(
        lich_hen, 'Tích điểm',
        f'Bạn vừa nhận {diem} điểm tích lũy!',
        f'Charm Spa cảm ơn bạn đã sử dụng {ten_dv} (lịch {lich_hen.ma_lh}, '
        f'{so_khach} khách). Bạn vừa được cộng {diem} điểm. '
        f'Tổng điểm hiện tại: {ket_qua.get("diem_sau", 0)}.',
    ):
        created += 1

    if ket_qua.get('len_hang') and ket_qua.get('hang_moi'):
        if _luu_thong_bao(
            lich_hen, 'Nâng hạng',
            f'Chúc mừng bạn lên hạng {ket_qua["hang_moi"]}!',
            f'Bạn đã đạt {ket_qua.get("diem_sau", 0)} điểm tích lũy '
            f'và được nâng lên hạng {ket_qua["hang_moi"]}. '
            'Cảm ơn bạn đã đồng hành cùng Charm Spa!',
        ):
            created += 1

    return created
