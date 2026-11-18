
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from accounts.models import NhanVien
from bookings.models import LichHen
from customers.models import KhachHang


# ==========================================================
# 1. CHƯƠNG TRÌNH ƯU ĐÃI
# ==========================================================

class ChuongTrinhUuDai(models.Model):

    KIEU_GIAM_CHOICES = [
        ('phan_tram', 'Giảm theo phần trăm'),
        ('so_tien', 'Giảm số tiền cố định'),
        ('gia_co_dinh', 'Giá ưu đãi cố định'),
    ]

    ma_ctud = models.CharField(
        max_length=10,
        primary_key=True,
        verbose_name="Mã ưu đãi"
    )

    ten_chuong_trinh = models.CharField(
        max_length=200,
        verbose_name="Tên chương trình"
    )

    mo_ta = models.TextField(
        null=True,
        blank=True,
        verbose_name="Mô tả"
    )

    loai_uu_dai = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Loại ưu đãi"
    )

    gia_tri_uu_dai = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Giá ưu đãi"
    )

    gia_goc = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Giá gốc"
    )

    thoi_luong = models.CharField(
        max_length=50,
        default="90 phút",
        verbose_name="Thời lượng liệu trình"
    )

    doi_tuong_ap_dung = models.CharField(
        max_length=100,
        default="Tất cả khách hàng",
        verbose_name="Đối tượng áp dụng"
    )

    dia_diem_ap_dung = models.CharField(
        max_length=200,
        default="Charm Grand Spa & Wellness",
        verbose_name="Địa điểm áp dụng"
    )

    ngay_bat_dau = models.DateTimeField(
        verbose_name="Ngày bắt đầu"
    )

    ngay_ket_thuc = models.DateTimeField(
        verbose_name="Ngày kết thúc"
    )

    quyen_loi = models.TextField(
        null=True,
        blank=True,
        verbose_name="Quyền lợi khách hàng"
    )

    dieu_kien = models.TextField(
        null=True,
        blank=True,
        verbose_name="Điều kiện áp dụng"
    )

    hinh_anh = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Hình ảnh Banner URL"
    )

    trang_thai = models.CharField(
        max_length=30,
        default='Đang áp dụng',
        verbose_name="Trạng thái"
    )

    # ------------------------------------------------------
    # CÁC TRƯỜNG MỚI: LIÊN KẾT ƯU ĐÃI VỚI DỊCH VỤ
    # ------------------------------------------------------

    ma_dv = models.ForeignKey(
        'services.DichVu',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cac_uu_dai',
        verbose_name='Dịch vụ áp dụng'
    )

    kieu_giam_gia = models.CharField(
        max_length=20,
        choices=KIEU_GIAM_CHOICES,
        default='gia_co_dinh',
        verbose_name='Kiểu giảm giá'
    )

    muc_giam = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Mức giảm'
    )

    # ------------------------------------------------------
    # KIỂM TRA DỮ LIỆU
    # ------------------------------------------------------

    def clean(self):
        super().clean()

        if self.ngay_bat_dau and self.ngay_ket_thuc:
            if self.ngay_ket_thuc <= self.ngay_bat_dau:
                raise ValidationError({
                    'ngay_ket_thuc':
                        'Ngày kết thúc phải sau ngày bắt đầu.'
                })

        if self.gia_goc is not None and self.gia_goc < 0:
            raise ValidationError({
                'gia_goc': 'Giá gốc không được âm.'
            })

        if self.gia_tri_uu_dai is not None:
            if self.gia_tri_uu_dai < 0:
                raise ValidationError({
                    'gia_tri_uu_dai':
                        'Giá ưu đãi không được âm.'
                })

        # Chưa liên kết dịch vụ: cho phép giữ dữ liệu cũ.
        if not self.ma_dv_id:
            return

        gia_dich_vu = self.ma_dv.gia_dich_vu

        if self.kieu_giam_gia == 'phan_tram':
            if not (Decimal('0') < self.muc_giam <= Decimal('100')):
                raise ValidationError({
                    'muc_giam':
                        'Phần trăm giảm phải lớn hơn 0 và không quá 100.'
                })

        elif self.kieu_giam_gia == 'so_tien':
            if not (Decimal('0') < self.muc_giam <= gia_dich_vu):
                raise ValidationError({
                    'muc_giam':
                        'Số tiền giảm phải lớn hơn 0 và không vượt giá dịch vụ.'
                })

        elif self.kieu_giam_gia == 'gia_co_dinh':
            if not (Decimal('0') <= self.muc_giam <= gia_dich_vu):
                raise ValidationError({
                    'muc_giam':
                        'Giá cố định phải từ 0 đến giá dịch vụ.'
                })

    # ------------------------------------------------------
    # TÍNH GIÁ ƯU ĐÃI
    # ------------------------------------------------------

    def tinh_gia_uu_dai(self):
        """
        Tính giá sau giảm dựa trên giá dịch vụ hiện tại.

        Hàm chỉ tính toán, không tự ghi dữ liệu vào DB.
        """
        if not self.ma_dv_id:
            return self.gia_tri_uu_dai

        gia_goc = self.ma_dv.gia_dich_vu
        muc_giam = self.muc_giam

        if self.kieu_giam_gia == 'phan_tram':
            gia_sau_giam = (
                gia_goc
                * (Decimal('100') - muc_giam)
                / Decimal('100')
            )

        elif self.kieu_giam_gia == 'so_tien':
            gia_sau_giam = gia_goc - muc_giam

        elif self.kieu_giam_gia == 'gia_co_dinh':
            gia_sau_giam = muc_giam

        else:
            return self.gia_tri_uu_dai

        gia_sau_giam = max(
            Decimal('0'),
            gia_sau_giam
        )

        return gia_sau_giam.quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )

    @property
    def so_tien_tiet_kiem(self):
        if self.ma_dv_id:
            gia_goc = self.ma_dv.gia_dich_vu
            return max(
                Decimal('0'),
                gia_goc - self.tinh_gia_uu_dai()
            )

        return max(
            Decimal('0'),
            self.gia_goc - self.gia_tri_uu_dai
        )

    def __str__(self):
        return self.ten_chuong_trinh


# ==========================================================
# 2. HƯỚNG DẪN CHĂM SÓC
# ==========================================================

class HuongDanChamSoc(models.Model):

    ma_hd = models.CharField(
        max_length=10,
        primary_key=True,
        verbose_name="Mã hướng dẫn"
    )

    ma_dv = models.ForeignKey(
        'services.DichVu',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Dịch vụ áp dụng"
    )

    tieu_de = models.CharField(
        max_length=150,
        verbose_name="Tiêu đề"
    )

    noi_dung = models.TextField(
        verbose_name="Nội dung hướng dẫn"
    )

    trang_thai = models.CharField(
        max_length=30,
        default='Hoạt động',
        verbose_name="Trạng thái"
    )

    def __str__(self):
        return self.tieu_de


# ==========================================================
# 3. THÔNG BÁO
# ==========================================================

class ThongBao(models.Model):

    ma_tb = models.CharField(
        max_length=10,
        primary_key=True,
        verbose_name="Mã thông báo"
    )

    ma_lh = models.ForeignKey(
        LichHen,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Lịch hẹn"
    )

    ma_ctud = models.ForeignKey(
        ChuongTrinhUuDai,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Chương trình ưu đãi"
    )

    ma_nv = models.ForeignKey(
        NhanVien,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Nhân viên tạo (nếu có)"
    )

    nguoi_gui = models.ForeignKey(
        'accounts.TaiKhoan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='thong_bao_da_gui',
        verbose_name="Tài khoản gửi thông báo"
    )

    loai_tb = models.CharField(
        max_length=50,
        verbose_name="Loại thông báo"
    )

    tieu_de = models.CharField(
        max_length=200,
        verbose_name="Tiêu đề"
    )

    noi_dung = models.TextField(
        verbose_name="Nội dung"
    )

    thoi_gian_tao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Thời gian tạo"
    )

    trang_thai = models.CharField(
        max_length=30,
        default='Chưa gửi',
        verbose_name="Trạng thái"
    )

    def __str__(self):
        return self.tieu_de


# ==========================================================
# 4. THÔNG BÁO KHÁCH HÀNG
# ==========================================================

class ThongBaoKhachHang(models.Model):

    ma_tbkh = models.CharField(
        max_length=10,
        primary_key=True,
        verbose_name="Mã chi tiết thông báo KH"
    )

    ma_tb = models.ForeignKey(
        ThongBao,
        on_delete=models.CASCADE,
        verbose_name="Thông báo"
    )

    ma_kh = models.ForeignKey(
        KhachHang,
        on_delete=models.CASCADE,
        verbose_name="Khách hàng nhận"
    )

    thoi_gian_gui = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Thời gian gửi"
    )

    trang_thai_gui = models.CharField(
        max_length=30,
        default='Chưa gửi',
        verbose_name="Trạng thái gửi"
    )


# ==========================================================
# 5. NHẬT KÝ GỬI HƯỚNG DẪN CHĂM SÓC
# ==========================================================

class NhatKyGuiHDCS(models.Model):

    ma_lh = models.ForeignKey(
        LichHen,
        on_delete=models.CASCADE,
        verbose_name="Lịch hẹn liên quan"
    )

    ma_hd = models.ForeignKey(
        HuongDanChamSoc,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Mẫu hướng dẫn"
    )

    ten_khach_hang = models.CharField(
        max_length=255,
        verbose_name="Tên khách hàng"
    )

    ten_dich_vu = models.CharField(
        max_length=255,
        verbose_name="Tên dịch vụ"
    )

    ten_ktv = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Kỹ thuật viên thực hiện"
    )

    gio_checkout = models.DateTimeField(
        default=timezone.now,
        verbose_name="Thời gian hoàn thành (Checkout)"
    )

    trang_thai = models.BooleanField(
        default=False,
        verbose_name="Trạng thái gửi HDCS (True: Đã gửi, False: Chưa gửi)"
    )

    noi_dung_gui = models.TextField(
        null=True,
        blank=True,
        verbose_name="Nội dung lời dặn thực tế đã gửi"
    )

    thoi_gian_gui = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Thời gian bấm gửi"
    )

    class Meta:
        verbose_name = "Nhật ký gửi HDCS"
        verbose_name_plural = "Nhật ký gửi HDCS"
        ordering = ['-gio_checkout']

    def __str__(self):
        return f"{self.ten_khach_hang} - {self.ten_dich_vu}"

class LichHenUuDai(models.Model):
    ma_lh = models.OneToOneField(
        'bookings.LichHen',
        on_delete=models.CASCADE,
        related_name='uu_dai_ap_dung',
        verbose_name='Lịch hẹn'
    )

    ma_ctud = models.ForeignKey(
        'notifications.ChuongTrinhUuDai',
        on_delete=models.PROTECT,
        related_name='lich_hen_su_dung',
        verbose_name='Chương trình ưu đãi'
    )

    gia_goc = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Giá gốc tại thời điểm đặt'
    )

    gia_sau_giam = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Giá sau giảm tại thời điểm đặt'
    )

    thoi_gian_ap_dung = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Thời gian áp dụng'
    )

    class Meta:
        verbose_name = 'Ưu đãi lịch hẹn'
        verbose_name_plural = 'Ưu đãi lịch hẹn'

    def __str__(self):
        return (
            f'{self.ma_lh_id} - '
            f'{self.ma_ctud.ten_chuong_trinh}'
        )

class LichHenUuDai(models.Model):
    ma_lh = models.OneToOneField(
        'bookings.LichHen',
        on_delete=models.CASCADE,
        related_name='uu_dai_ap_dung',
        verbose_name='Lịch hẹn'
    )

    ma_ctud = models.ForeignKey(
        'notifications.ChuongTrinhUuDai',
        on_delete=models.PROTECT,
        related_name='lich_hen_su_dung',
        verbose_name='Chương trình ưu đãi'
    )

    gia_goc = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Tổng giá gốc tại thời điểm đặt'
    )

    gia_sau_giam = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Tổng giá sau giảm tại thời điểm đặt'
    )

    thoi_gian_ap_dung = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Thời gian áp dụng'
    )

    class Meta:
        verbose_name = 'Ưu đãi lịch hẹn'
        verbose_name_plural = 'Ưu đãi lịch hẹn'

    def __str__(self):
        return f'{self.ma_lh_id} - {self.ma_ctud.ten_chuong_trinh}'
