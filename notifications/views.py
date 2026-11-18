from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from uuid import uuid4
from functools import wraps
from accounts.models import (
    TaiKhoan, is_manager_role, is_staff_portal_user, is_customer_role
)
from .models import ThongBao, ThongBaoKhachHang, ChuongTrinhUuDai, NhatKyGuiHDCS
from django.http import JsonResponse, Http404, HttpResponseForbidden
from customers.models import KhachHang
from bookings.models import LichHen, PhanCongLichHen
from services.models import DichVu
from .models import HuongDanChamSoc


# Sử dụng duy nhất quyền nghiệp vụ theo TaiKhoan.vai_tro.
# Không dùng Django user.is_staff/is_superuser cho portal website.
LOGIN_URL = '/accounts/dang_nhap/'


def permission_required(check, *, json_response=False):
    """Redirect anonymous visitors to login; return HTTP 403 for wrong business role."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url=LOGIN_URL)
        def inner(request, *args, **kwargs):
            if not check(request.user):
                if json_response:
                    return JsonResponse(
                        {'success': False, 'error': 'Bạn không có quyền thực hiện thao tác này.'},
                        status=403,
                    )
                return HttpResponseForbidden('Bạn không có quyền truy cập chức năng này.')
            return view_func(request, *args, **kwargs)
        return inner
    return decorator


def _khach_hang_cua_user(user):
    # Không tra cứu theo username trùng số điện thoại của người khác.
    return KhachHang.objects.filter(ma_tk__user=user).first()


def _khoang_ngay(request):
    # Hai ngày form HTML loại date; áp dụng từ 00:00 ngày bắt đầu
    # đến hết 23:59:59 ngày kết thúc theo múi giờ Django.
    ngay_bd_str = (request.POST.get('ngay_bat_dau') or '').strip()
    ngay_kt_str = (request.POST.get('ngay_ket_thuc') or '').strip()
    if not ngay_bd_str or not ngay_kt_str:
        raise ValueError('Vui lòng chọn đầy đủ ngày bắt đầu và ngày kết thúc.')
    try:
        bd = datetime.strptime(ngay_bd_str, '%Y-%m-%d').date()
        kt = datetime.strptime(ngay_kt_str, '%Y-%m-%d').date()
    except ValueError as exc:
        raise ValueError('Ngày phải có định dạng YYYY-MM-DD.') from exc
    if kt < bd:
        raise ValueError('Ngày kết thúc phải bằng hoặc sau ngày bắt đầu.')
    tz = timezone.get_current_timezone()
    bat_dau = timezone.make_aware(datetime.combine(bd, time.min), tz)
    ket_thuc = timezone.make_aware(datetime.combine(kt + timedelta(days=1), time.min), tz) - timedelta(microseconds=1)
    return bat_dau, ket_thuc


def _trang_thai_theo_ngay(bat_dau, ket_thuc):
    hien_tai = timezone.now()
    if hien_tai < bat_dau:
        return 'Sắp diễn ra'
    if hien_tai > ket_thuc:
        return 'Đã kết thúc'
    return 'Đang áp dụng'


def _gia_tien(post, field, default='0'):
    raw = (post.get(field) or default).strip()
    try:
        gia = Decimal(raw)
    except (InvalidOperation, ValueError):
        raise ValueError(f'Giá trị {field} không hợp lệ.')
    if not gia.is_finite() or gia < 0 or gia > Decimal('9999999999.99'):
        raise ValueError(f'Giá trị {field} phải là số không âm, tối đa 9.999.999.999,99.')
    if gia.as_tuple().exponent < -2:
        raise ValueError(f'Giá trị {field} tối đa 2 chữ số thập phân.')
    return gia


def _ma_uu_dai_moi():
    # Khóa chính tối đa 10 ký tự, tránh trùng khi đã xóa bản ghi cũ.
    for _ in range(10):
        ma = 'CT' + uuid4().hex[:8].upper()
        if not ChuongTrinhUuDai.objects.filter(pk=ma).exists():
            return ma
    raise ValueError('Không thể tạo mã ưu đãi mới, vui lòng thử lại.')


# =====================================================================
# 1. TRUNG TÂM THÔNG BÁO CỦA KHÁCH HÀNG & HỆ THỐNG
# =====================================================================
@login_required(login_url=LOGIN_URL)
@user_passes_test(is_customer_role, login_url=LOGIN_URL)
def danh_sach_thong_bao(request):
    """
    Trang Trung tâm thông báo của khách hàng (Truy vấn chuẩn xác theo KhachHang instance)
    """
    # Lấy chính xác đối tượng KhachHang tương ứng với tài khoản đang đăng nhập
    khach_hang = _khach_hang_cua_user(request.user)

    if khach_hang:
        thong_bao_list = list(
            ThongBaoKhachHang.objects.filter(
                ma_kh=khach_hang
            ).select_related('ma_tb', 'ma_tb__ma_ctud').order_by('-thoi_gian_gui')
        )
        # Tuong thich voi template cu dung tb.tieu_de / tb.noi_dung.
        for tb in thong_bao_list:
            tb.tieu_de = tb.ma_tb.tieu_de
            tb.noi_dung = tb.ma_tb.noi_dung
            tb.loai_tb = tb.ma_tb.loai_tb
            tb.ma_ctud = tb.ma_tb.ma_ctud
            tb.da_doc = tb.trang_thai_gui == 'Đã đọc'
    else:
        thong_bao_list = []

    context = {
        'thong_bao_list': thong_bao_list,
    }
    return render(request, 'notifications/danh_sach_thong_bao.html', context)


@login_required(login_url=LOGIN_URL)
@user_passes_test(is_customer_role, login_url=LOGIN_URL)
@require_POST
def danh_dau_da_doc(request, ma_tbkh):
    """
    Đánh dấu thông báo là đã đọc một cách an toàn
    """
    khach_hang = _khach_hang_cua_user(request.user)

    if khach_hang:
        tb = get_object_or_404(
            ThongBaoKhachHang,
            ma_tbkh=ma_tbkh, ma_kh=khach_hang
        )
        tb.trang_thai_gui = 'Đã đọc'
        tb.save()

    return redirect('notifications:danh_sach_thong_bao')


# =====================================================================
# 2. MODULE ƯU ĐÃI (PROMOTIONS)
# =====================================================================

def danh_sach_uu_dai(request):
    hien_tai = timezone.now()
    promotions = ChuongTrinhUuDai.objects.filter(
        trang_thai='Đang áp dụng',
        ngay_bat_dau__lte=hien_tai,
        ngay_ket_thuc__gte=hien_tai,
        gia_tri_uu_dai__gt=0
    ).exclude(ten_chuong_trinh__isnull=True).order_by('-ngay_bat_dau', '-pk')

    context = {
        'promotions': promotions,
        'danh_sach': promotions,
    }
    return render(request, 'notifications/danh_sach_uu_dai.html', context)


def chi_tiet_uu_dai(request, promo_code):
    hien_tai = timezone.now()
    promo = get_object_or_404(
        ChuongTrinhUuDai, pk=promo_code,
        trang_thai='Đang áp dụng',
        ngay_bat_dau__lte=hien_tai,
        ngay_ket_thuc__gte=hien_tai,
    )
    context = {
        'promo': promo,
    }
    return render(request, 'notifications/chi_tiet_uu_dai.html', context)


@permission_required(is_staff_portal_user)
def admin_promotion_list(request):
    ds_uu_dai = ChuongTrinhUuDai.objects.select_related('ma_dv').all().order_by('-pk')
    hien_tai = timezone.now()
    dang_ap_dung_count = ds_uu_dai.filter(
        trang_thai='Đang áp dụng',
        ngay_bat_dau__lte=hien_tai,
        ngay_ket_thuc__gte=hien_tai
    ).count()
    sap_dien_ra_count = ds_uu_dai.filter(
        trang_thai='Sắp diễn ra', ngay_bat_dau__gt=hien_tai
    ).count()

    # Cung cap danh sach dich vu cho popup them/sua uu dai.
    # Template cu van hoat dong neu chua dung cac bien moi.
    ds_dich_vu = DichVu.objects.all().order_by('ten_dich_vu', 'ma_dv')
    context = {
        'ds_uu_dai': ds_uu_dai,
        'dang_ap_dung_count': dang_ap_dung_count,
        'sap_dien_ra_count': sap_dien_ra_count,
        'promotions': ds_uu_dai,
        'ds_dich_vu': ds_dich_vu,
        'dich_vu_list': ds_dich_vu,
        'can_manage_promotions': is_manager_role(request.user),
        'active_menu': 'promotions',
    }
    return render(request, 'notifications/admin_promotion_list.html', context)


@permission_required(is_manager_role, json_response=True)
@require_POST
def api_them_hoac_sua_uu_dai(request):
    """Quan ly them/sua uu dai: moi uu dai lien ket toi mot DichVu.

    - Backend tu lay gia DichVu, khong tin gia goc/gia uu dai gui tu form.
    - Ho tro 3 kieu giam; giu du lieu uu dai cu chua co ma_dv.
    - Mau form cu co the sua ban ghi cu; tao moi phai chon dich vu.
    """
    try:
        pk = (request.POST.get('id') or '').strip()
        uu_dai = get_object_or_404(ChuongTrinhUuDai, pk=pk) if pk else None
        tieu_de = (request.POST.get('tieu_de') or request.POST.get('ten_chuong_trinh') or '').strip()
        if not tieu_de or len(tieu_de) > 200:
            raise ValueError('Ten chuong trinh phai co tu 1 den 200 ky tu.')

        bat_dau, ket_thuc = _khoang_ngay(request)
        ma_dv = (request.POST.get('ma_dv') or '').strip()
        kieu_giam = (request.POST.get('kieu_giam_gia') or '').strip()
        raw_muc_giam = (request.POST.get('muc_giam') or '').strip()

        # Form UI cu chua co cac truong moi: neu sua uu dai da gan
        # dich vu, giu nguyen cau hinh giam gia hien tai.
        # Neu sua uu dai cu chua lien ket dich vu, giu gia cu.
        co_du_lieu_moi = bool(ma_dv or kieu_giam or raw_muc_giam)
        if co_du_lieu_moi:
            if not ma_dv:
                raise ValueError('Vui long chon dich vu ap dung.')
            dich_vu = DichVu.objects.filter(pk=ma_dv).first()
            if dich_vu is None:
                raise ValueError('Dich vu khong ton tai.')
            if kieu_giam not in dict(ChuongTrinhUuDai.KIEU_GIAM_CHOICES):
                raise ValueError('Kieu giam gia khong hop le.')
            muc_giam = _gia_tien(request.POST, 'muc_giam', default='')
        elif uu_dai is not None and uu_dai.ma_dv_id:
            dich_vu = uu_dai.ma_dv
            kieu_giam = uu_dai.kieu_giam_gia
            muc_giam = uu_dai.muc_giam
        elif uu_dai is not None:
            # Du lieu cu chua duoc gan DichVu, chi cho phep cap nhat
            # thong tin va gia cu. Can gan DichVu de ap dung dat lich.
            dich_vu = None
            kieu_giam = uu_dai.kieu_giam_gia
            muc_giam = uu_dai.muc_giam
        else:
            raise ValueError('Vui long chon dich vu, kieu giam gia va muc giam.')

        du_lieu = {
            'ten_chuong_trinh': tieu_de,
            'mo_ta': (request.POST.get('mo_ta') or '').strip(),
            'loai_uu_dai': (request.POST.get('loai_uu_dai') or '').strip(),
            'ngay_bat_dau': bat_dau,
            'ngay_ket_thuc': ket_thuc,
            'thoi_luong': (request.POST.get('thoi_luong') or '90 phut').strip(),
            'doi_tuong_ap_dung': (request.POST.get('doi_tuong_ap_dung') or 'Tất cả khách hàng').strip(),
            'dia_diem_ap_dung': (request.POST.get('dia_diem_ap_dung') or 'Charm Grand Spa & Wellness').strip(),
            'quyen_loi': (request.POST.get('quyen_loi') or '').strip(),
            'dieu_kien': (request.POST.get('dieu_kien') or '').strip(),
            'ma_dv': dich_vu,
            'kieu_giam_gia': kieu_giam,
            'muc_giam': muc_giam,
        }

        for field, length in [('loai_uu_dai', 50), ('thoi_luong', 50),
                              ('doi_tuong_ap_dung', 100), ('dia_diem_ap_dung', 200)]:
            if len(du_lieu[field]) > length:
                raise ValueError(f'Truong {field} vuot qua {length} ky tu.')
        anh = (request.POST.get('hinh_anh') or '').strip()
        if len(anh) > 500:
            raise ValueError('URL hinh anh toi da 500 ky tu.')
        if anh or uu_dai is None:
            du_lieu['hinh_anh'] = anh

        trang_thai_yeu_cau = (request.POST.get('trang_thai') or '').strip()
        du_lieu['trang_thai'] = (
            trang_thai_yeu_cau if trang_thai_yeu_cau in ('Tạm dừng', 'Ngừng áp dụng')
            else _trang_thai_theo_ngay(bat_dau, ket_thuc)
        )

        if uu_dai is None:
            uu_dai = ChuongTrinhUuDai(ma_ctud=_ma_uu_dai_moi())
        for field, value in du_lieu.items():
            setattr(uu_dai, field, value)

        if dich_vu is not None:
            # Tinh tren server, khong dung hai gia do browser gui len.
            uu_dai.gia_goc = dich_vu.gia_dich_vu
            uu_dai.gia_tri_uu_dai = uu_dai.tinh_gia_uu_dai()
            if uu_dai.gia_tri_uu_dai <= 0:
                raise ValueError('Gia sau giam phai lon hon 0.')
            if uu_dai.gia_tri_uu_dai > uu_dai.gia_goc:
                raise ValueError('Gia uu dai khong duoc lon hon gia goc.')
        else:
            uu_dai.gia_goc = _gia_tien(request.POST, 'gia_goc', default=str(uu_dai.gia_goc or 0))
            uu_dai.gia_tri_uu_dai = _gia_tien(
                request.POST, 'gia_tri_uu_dai', default=str(uu_dai.gia_tri_uu_dai or 0)
            )
            if uu_dai.gia_tri_uu_dai <= 0 or (
                uu_dai.gia_goc and uu_dai.gia_tri_uu_dai > uu_dai.gia_goc
            ):
                raise ValueError('Gia uu dai phai duong va khong vuot gia goc.')

        # full_clean() kiem tra ca quy tac model; save() mot minh khong tu kiem tra.
        uu_dai.full_clean()
        uu_dai.save()
        return JsonResponse({
            'success': True,
            'message': 'Cập nhật thành công!' if pk else 'Thêm mới thành công!',
            'ma_ctud': uu_dai.pk,
            'gia_goc': str(uu_dai.gia_goc),
            'gia_tri_uu_dai': str(uu_dai.gia_tri_uu_dai),
        })
    except (ValueError, ValidationError) as exc:
        if isinstance(exc, ValidationError):
            loi = '; '.join(exc.messages)
        else:
            loi = str(exc)
        return JsonResponse({'success': False, 'error': loi}, status=400)


@permission_required(is_manager_role, json_response=True)
@require_POST
def api_gui_thong_bao_uu_dai(request):
    """
    API xử lý gửi thông báo ưu đãi trực tiếp đến đối tượng KhachHang chuẩn xác 100%
    """
    try:
        promo_id = (request.POST.get('promo_id') or '').strip()
        if not promo_id:
            return JsonResponse({'success': False, 'error': 'Thiếu mã chương trình ưu đãi.'}, status=400)

        now = timezone.now()
        promo = get_object_or_404(ChuongTrinhUuDai, pk=promo_id)
        if not (promo.trang_thai == 'Đang áp dụng' and
                promo.ngay_bat_dau <= now <= promo.ngay_ket_thuc):
            return JsonResponse({'success': False,
                                 'error': 'Chỉ gửi thông báo cho ưu đãi đang có hiệu lực.'}, status=400)
        raw_doi_tuong = (
            request.POST.get('doi_tuong')
            or request.POST.get('doi_tuong_ap_dung')
            or request.POST.get('hang_thanh_vien')
            or ''
        )
        doi_tuong = raw_doi_tuong.strip().lower()

        if not doi_tuong or 'tat_ca' in doi_tuong or 'tất cả' in doi_tuong or doi_tuong in ('all', 'all_customers'):
            khach_hang_records = KhachHang.objects.all()
        elif 'đồng' in doi_tuong or 'dong' in doi_tuong:
            khach_hang_records = KhachHang.objects.filter(ma_tv__ten_hang__icontains='Đồng')
        elif 'bạc' in doi_tuong or 'bac' in doi_tuong:
            khach_hang_records = KhachHang.objects.filter(ma_tv__ten_hang__icontains='Bạc')
        elif 'vàng' in doi_tuong or 'vang' in doi_tuong:
            khach_hang_records = KhachHang.objects.filter(ma_tv__ten_hang__icontains='Vàng')
        elif 'kim cương' in doi_tuong or 'kim_cuong' in doi_tuong:
            khach_hang_records = KhachHang.objects.filter(ma_tv__ten_hang__icontains='Kim Cương')
        else:
            return JsonResponse({'success': False, 'error': 'Đối tượng nhận không hợp lệ.'}, status=400)

        danh_sach_kh = list(khach_hang_records.distinct())
        if not danh_sach_kh:
            return JsonResponse({'success': False, 'error': 'Không tìm thấy khách hàng thuộc nhóm đã chọn.'}, status=400)

        # Admin gui truc tiep: lay TaiKhoan lien ket User dang dang nhap.
        tai_khoan_gui = TaiKhoan.objects.filter(user=request.user).first()
        if tai_khoan_gui is None:
            return JsonResponse({
                'success': False,
                'error': 'Tài khoản quản lý chưa có hồ sơ TaiKhoan.'
            }, status=400)

        ngay_bd = promo.ngay_bat_dau.strftime('%d/%m/%Y') if promo.ngay_bat_dau else ''
        ngay_kt = promo.ngay_ket_thuc.strftime('%d/%m/%Y') if promo.ngay_ket_thuc else ''
        tieu_de = f'Ưu đãi đặc quyền: {promo.ten_chuong_trinh}'
        noi_dung = (
            f'{promo.ten_chuong_trinh}. '
            f'Giá ưu đãi: {promo.gia_tri_uu_dai:,.0f}đ; '
            f'giá gốc: {promo.gia_goc:,.0f}đ. '
            f'Áp dụng từ {ngay_bd} đến {ngay_kt}. '
            f'Địa điểm: {promo.dia_diem_ap_dung}.'
        )
        thoi_diem_gui = timezone.now()

        with transaction.atomic():
            thong_bao = ThongBao.objects.create(
                ma_tb='TB' + uuid4().hex[:8].upper(),
                ma_ctud=promo,
                ma_nv=None,
                nguoi_gui=tai_khoan_gui,
                loai_tb='Ưu đãi',
                tieu_de=tieu_de,
                noi_dung=noi_dung,
                trang_thai='Đã gửi'
            )
            # Tao tung ban ghi de co the xac nhan dung so luong duoc luu.
            for kh in danh_sach_kh:
                ThongBaoKhachHang.objects.create(
                    ma_tbkh='TK' + uuid4().hex[:8].upper(),
                    ma_tb=thong_bao,
                    ma_kh=kh,
                    thoi_gian_gui=thoi_diem_gui,
                    trang_thai_gui='Chưa đọc'
                )

        return JsonResponse({
            'success': True,
            'message': f'Đã gửi thông báo ưu đãi đến {len(danh_sach_kh)} khách hàng!',
            'so_nguoi_nhan': len(danh_sach_kh)
        })
    except Exception:
        return JsonResponse({'success': False, 'error': 'Không thể gửi thông báo. Vui lòng thử lại.'}, status=500)


@permission_required(is_staff_portal_user, json_response=True)
def get_promotion_detail(request, ma_ctud):
    promo = get_object_or_404(ChuongTrinhUuDai, pk=ma_ctud)
    data = {
        'ma_ctud': getattr(promo, 'ma_ctud', str(promo.pk)),
        'ten_chuong_trinh': getattr(promo, 'ten_chuong_trinh', ''),
        'ma_dv': promo.ma_dv_id or '',
        'kieu_giam_gia': promo.kieu_giam_gia,
        'muc_giam': str(promo.muc_giam),
        'gia_goc': str(promo.gia_goc),
        'gia_tri_uu_dai': str(promo.gia_tri_uu_dai),
    }
    return JsonResponse(data)


@permission_required(is_manager_role)
@require_POST
def xoa_uu_dai(request, ma_ctud):
    promo = get_object_or_404(ChuongTrinhUuDai, pk=ma_ctud)
    promo.delete()
    return redirect('notifications:admin_promotion_list')


@permission_required(is_manager_role)
def them_uu_dai(request):
    return redirect('notifications:admin_promotion_list')


@permission_required(is_manager_role)
def chinh_sua_uu_dai(request, ma_ctud):
    return redirect('notifications:admin_promotion_list')


# =====================================================================
# 3. MODULE CHĂM SÓC SAU LIỆU TRÌNH (AFTERCARE)
# =====================================================================
@login_required(login_url=LOGIN_URL)
@user_passes_test(is_staff_portal_user, login_url=LOGIN_URL)
def cham_soc_sau_lieu_trinh(request):
    """Doc lich hoan thanh va tao nhat ky HDCS neu chua co.

    Khong sua du lieu bookings; khong gui thong bao trong GET.
    gio_checkout o day la thoi diem ghi nhan nhat ky, KHONG phai
    gio checkout thuc te vi LichHen chua luu tru thong tin nay.
    """
    lich_da_hoan_thanh = (
        LichHen.objects.filter(trang_thai='Hoàn thành')
        .select_related('ma_kh', 'ma_dv', 'ma_nv')
        .order_by('-ngay_hen', '-gio_hen')
    )

    # Chi tao nhat ky cho nhung lich chua tung co nhat ky.
    existing_ids = set(
        NhatKyGuiHDCS.objects.values_list('ma_lh_id', flat=True)
    )
    for lh in lich_da_hoan_thanh:
        if lh.pk in existing_ids:
            continue

        phan_cong = list(
            PhanCongLichHen.objects.filter(ma_lh=lh)
            .select_related('ma_nv_phu_trach')
            .order_by('ngay_phan_cong', 'pk')
        )
        if phan_cong:
            ten_ktv = ', '.join(dict.fromkeys(
                pc.ma_nv_phu_trach.ho_ten for pc in phan_cong
            ))
        elif lh.ma_nv_id:
            ten_ktv = lh.ma_nv.ho_ten
        else:
            ten_ktv = 'Chưa phân công'

        mau_hd = HuongDanChamSoc.objects.filter(
            ma_dv=lh.ma_dv, trang_thai='Hoạt động'
        ).first()

        # get_or_create de tranh tao lap neu nap lai trang.
        NhatKyGuiHDCS.objects.get_or_create(
            ma_lh=lh,
            defaults={
                'ma_hd': mau_hd,
                'ten_khach_hang': lh.ma_kh.ho_ten,
                'ten_dich_vu': lh.ma_dv.ten_dich_vu,
                'ten_ktv': ten_ktv,
                'gio_checkout': timezone.now(),
                'trang_thai': False,
            }
        )
        existing_ids.add(lh.pk)

    records = list(
        NhatKyGuiHDCS.objects
        .select_related('ma_lh', 'ma_lh__ma_dv', 'ma_hd')
        .order_by('-gio_checkout', '-pk')
    )
    # Chi cho phep mau dang hoat dong va dung dich vu (hoac mau chung).
    mau_huong_dan = list(
        HuongDanChamSoc.objects.filter(trang_thai='Hoạt động')
        .select_related('ma_dv').order_by('tieu_de')
    )
    return render(request, 'notifications/cham_soc_sau_lieu_trinh.html', {
        'records': records,
        'mau_huong_dan': mau_huong_dan,
    })


@login_required(login_url=LOGIN_URL)
@user_passes_test(is_staff_portal_user, login_url=LOGIN_URL)
@require_POST
def gui_hdcs_action(request, id):
    """Gui HDCS den dung khach cua lich hen, chi gui mot lan / nhat ky."""
    ma_mau = (request.POST.get('ma_hd') or '').strip()
    ghi_chu = (request.POST.get('ghi_chu') or '').strip()
    # Khong tin du lieu mau gui tu browser, lay mau tren server de chong sua gia.
    if len(ghi_chu) > 5000:
        return JsonResponse({'success': False, 'error': 'Ghi chú tối đa 5.000 ký tự.'}, status=400)
    if not ma_mau and not ghi_chu:
        return JsonResponse({'success': False, 'error': 'Hãy chọn mẫu hoặc nhập ghi chú riêng.'}, status=400)

    tai_khoan_gui = TaiKhoan.objects.filter(user=request.user).first()
    if tai_khoan_gui is None:
        return JsonResponse({
            'success': False,
            'error': 'Tài khoản chưa có hồ sơ TaiKhoan, không thể xác định người gửi.'
        }, status=400)

    with transaction.atomic():
        record = get_object_or_404(
            NhatKyGuiHDCS.objects.select_for_update().select_related('ma_lh__ma_kh'),
            pk=id
        )
        if record.trang_thai:
            return JsonResponse({
                'success': False, 'error': 'Hướng dẫn này đã được gửi trước đó.'
            }, status=409)

        if record.ma_lh.trang_thai != 'Hoàn thành':
            return JsonResponse({
                'success': False,
                'error': 'Chỉ được gửi HDCS cho lịch hẹn đã Hoàn thành.'
            }, status=400)

        mau = None
        if ma_mau:
            mau = HuongDanChamSoc.objects.filter(
                pk=ma_mau, trang_thai='Hoạt động'
            ).first()
            if mau is None or (mau.ma_dv_id is not None and
                                mau.ma_dv_id != record.ma_lh.ma_dv_id):
                return JsonResponse({
                    'success': False, 'error': 'Mẫu hướng dẫn không hợp lệ hoặc không phù hợp dịch vụ.'
                }, status=400)

        khach_hang = record.ma_lh.ma_kh
        thoi_diem = timezone.now()
        tieu_de = f'Hướng dẫn chăm sóc sau liệu trình - {record.ten_dich_vu}'
        noi_dung_parts = [
            'CHARM GRAND SPA & WELLNESS',
            'HƯỚNG DẪN CHĂM SÓC SAU LIỆU TRÌNH',
            '',
            f'Kính gửi Quý khách {record.ten_khach_hang},',
            f'Cảm ơn Quý khách đã trải nghiệm dịch vụ {record.ten_dich_vu} tại Charm Grand Spa.',
        ]
        if mau:
            noi_dung_parts.extend(['', 'HƯỚNG DẪN TỪ CHUYÊN VIÊN', mau.tieu_de, mau.noi_dung.strip()])
        if ghi_chu:
            noi_dung_parts.extend(['', 'GHI CHÚ RIÊNG DÀNH CHO QUÝ KHÁCH', ghi_chu])
        noi_dung_parts.extend(['', 'LỜI NHẮN TỪ CHARM',
                               'Charm Grand Spa cảm ơn Quý khách và mong sớm được đón tiếp Quý khách trở lại.'])
        noi_dung = '\n'.join(noi_dung_parts)
        if len(noi_dung) > 12000:
            return JsonResponse({'success': False, 'error': 'Nội dung gửi quá dài.'}, status=400)

        thong_bao = ThongBao.objects.create(
            ma_tb='TB' + uuid4().hex[:8].upper(),
            ma_lh=record.ma_lh,
            ma_ctud=None,
            ma_nv=None,
            nguoi_gui=tai_khoan_gui,
            loai_tb='Chăm sóc sau liệu trình',
            tieu_de=tieu_de,
            noi_dung=noi_dung,
            trang_thai='Đã gửi',
        )
        ThongBaoKhachHang.objects.create(
            ma_tbkh='TK' + uuid4().hex[:8].upper(),
            ma_tb=thong_bao,
            ma_kh=khach_hang,
            thoi_gian_gui=thoi_diem,
            trang_thai_gui='Chưa đọc',
        )

        record.ma_hd = mau
        record.noi_dung_gui = noi_dung
        record.thoi_gian_gui = thoi_diem
        record.trang_thai = True
        record.save(update_fields=['ma_hd', 'noi_dung_gui', 'thoi_gian_gui', 'trang_thai'])

    return JsonResponse({
        'success': True,
        'message': f'Đã gửi HDCS cho {record.ten_khach_hang}!',
    })


@login_required(login_url=LOGIN_URL)
@user_passes_test(is_staff_portal_user, login_url=LOGIN_URL)
def get_hdcs_detail(request, id):
    record = get_object_or_404(NhatKyGuiHDCS, pk=id)
    return JsonResponse({
        'id': record.pk,
        'noi_dung': record.noi_dung_gui or '',
        'trang_thai': record.trang_thai,
        'thoi_gian_gui': timezone.localtime(record.thoi_gian_gui).strftime('%d/%m/%Y %H:%M')
        if record.thoi_gian_gui else None,
    })


@login_required(login_url=LOGIN_URL)
@user_passes_test(is_customer_role, login_url=LOGIN_URL)
def customer_aftercare_detail(request, id):
    khach_hang = _khach_hang_cua_user(request.user)
    if khach_hang is None:
        raise Http404('Không tìm thấy hồ sơ khách hàng.')
    record = get_object_or_404(NhatKyGuiHDCS, pk=id, ma_lh__ma_kh=khach_hang,
                               trang_thai=True)
    context = {
        'record': record,
    }
    return render(request, 'notifications/customer_aftercare_detail.html', context)


@login_required(login_url=LOGIN_URL)
@user_passes_test(is_staff_portal_user, login_url=LOGIN_URL)
def lich_hen_chu_ky_cham_soc(request):
    context = {}
    return render(request, 'notifications/lich_hen_chu_ky_cham_soc.html', context)


@login_required(login_url=LOGIN_URL)
def dat_lich_tai_hen_nhanh(request):
    return redirect('notifications:danh_sach_thong_bao')
