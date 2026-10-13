from django.db import models
from customers.models import KhachHang
from accounts.models import TaiKhoan, NhanVien
from services.models import DichVu


class PhanHoiKhieuNai(models.Model):
    LOAI_PH_CHOICES = [('Phản hồi', 'Phản hồi'), ('Khiếu nại', 'Khiếu nại')]
    TRANG_THAI_CHOICES = [('Đã tiếp nhận', 'Đã tiếp nhận'), ('Đang xử lý', 'Đang xử lý'), ('Đã giải quyết', 'Đã giải quyết')]
    TINH_HOP_LE_CHOICES = [('Hợp lệ', 'Hợp lệ'), ('Không hợp lệ', 'Không hợp lệ')]
    LY_DO_KHONG_HOP_LE_CHOICES = [('Gửi nhầm', 'Gửi nhầm'), ('Trùng lặp', 'Trùng lặp'), ('Spam', 'Spam'), ('Nội dung không liên quan', 'Nội dung không liên quan'), ('Khác', 'Khác')]

    ma_ph = models.CharField(max_length=20, primary_key=True, verbose_name="Mã phản hồi/khiếu nại")
    ma_kh = models.ForeignKey(KhachHang, on_delete=models.PROTECT, related_name='phan_hoi_khieu_nai', verbose_name="Khách hàng")
    ma_dv = models.ForeignKey(DichVu, on_delete=models.SET_NULL, null=True, blank=True, related_name='phan_hoi_khieu_nai', verbose_name="Dịch vụ liên quan")
    loai_ph = models.CharField(max_length=20, choices=LOAI_PH_CHOICES, verbose_name="Loại")
    tieu_de = models.CharField(max_length=255, verbose_name="Tiêu đề")
    noi_dung = models.TextField(verbose_name="Nội dung chi tiết")
    trang_thai_xu_ly = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='Đã tiếp nhận', verbose_name="Trạng thái xử lý")
    tinh_hop_le = models.CharField(max_length=20, choices=TINH_HOP_LE_CHOICES, default='Hợp lệ', verbose_name="Tính hợp lệ")
    ly_do_khong_hop_le = models.CharField(max_length=255, choices=LY_DO_KHONG_HOP_LE_CHOICES, null=True, blank=True, verbose_name="Lý do không hợp lệ")
    chi_tiet_ly_do = models.CharField(max_length=255, null=True, blank=True, verbose_name="Chi tiết lý do")
    ngay_gui = models.DateTimeField(auto_now_add=True, verbose_name="Ngày gửi")
    ngay_cap_nhat = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")
    ngay_giai_quyet = models.DateTimeField(null=True, blank=True, verbose_name="Ngày giải quyết")

    class Meta:
        db_table = 'PHAN_HOI_KHIEU_NAI'

    def __str__(self):
        return f"{self.ma_ph} - {self.tieu_de}"


class PhanCongXuLy(models.Model):
    ma_pc = models.CharField(max_length=20, primary_key=True, verbose_name="Mã phân công")
    ma_ph = models.ForeignKey(PhanHoiKhieuNai, on_delete=models.CASCADE, related_name='phan_cong', verbose_name="Phiếu phản hồi")
    ma_nv = models.ForeignKey(NhanVien, on_delete=models.PROTECT, related_name='phan_cong_xu_ly', verbose_name="Nhân viên xử lý")
    ma_nguoi_phan_cong = models.ForeignKey(TaiKhoan, on_delete=models.PROTECT, related_name='phan_cong_da_thuc_hien', verbose_name="Quản trị viên phân công")
    thoi_gian_pc = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian phân công")
    thoi_gian_ket_thuc = models.DateTimeField(null=True, blank=True, verbose_name="Thời gian kết thúc phụ trách")

    class Meta:
        db_table = 'PHAN_CONG_XU_LY'

    def __str__(self):
        return self.ma_pc


class LichSuXuLy(models.Model):
    LOAI_THAO_TAC_CHOICES = [('Phân công', 'Phân công'), ('Cập nhật trạng thái', 'Cập nhật trạng thái'), ('Cập nhật xử lý', 'Cập nhật xử lý'), ('Đánh dấu không hợp lệ', 'Đánh dấu không hợp lệ'), ('Hoàn tất xử lý', 'Hoàn tất xử lý')]

    ma_ls = models.CharField(max_length=20, primary_key=True, verbose_name="Mã lịch sử xử lý")
    ma_ph = models.ForeignKey(PhanHoiKhieuNai, on_delete=models.CASCADE, related_name='lich_su_xu_ly', verbose_name="Phiếu phản hồi")
    ma_nguoi_thuc_hien = models.ForeignKey(TaiKhoan, on_delete=models.PROTECT, related_name='lich_su_da_thuc_hien', verbose_name="Người thực hiện")
    loai_thao_tac = models.CharField(max_length=50, choices=LOAI_THAO_TAC_CHOICES, verbose_name="Loại thao tác")
    noi_dung = models.TextField(null=True, blank=True, verbose_name="Chi tiết thao tác")
    ngay_thuc_hien = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian")

    class Meta:
        db_table = 'LICH_SU_XU_LY'
        ordering = ['ngay_thuc_hien']

    def __str__(self):
        return f"{self.loai_thao_tac} - {self.ma_ph}"


class TepDinhKem(models.Model):
    ma_tep = models.CharField(max_length=20, primary_key=True, verbose_name="Mã tệp")
    ma_ph = models.ForeignKey(PhanHoiKhieuNai, on_delete=models.CASCADE, related_name='tep_dinh_kem', verbose_name="Phiếu phản hồi")
    ten_tep = models.CharField(max_length=255, verbose_name="Tên tệp")
    duong_dan_tep = models.CharField(max_length=255, verbose_name="Đường dẫn")
    loai_tep = models.CharField(max_length=50, verbose_name="Loại tệp")
    ngay_tai_len = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tải lên")

    class Meta:
        db_table = 'TEP_DINH_KEM'

    def __str__(self):
        return self.ten_tep