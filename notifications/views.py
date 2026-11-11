from datetime import date, datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from uuid import uuid4
from accounts.models import TaiKhoan
from .models import ThongBao, ThongBaoKhachHang, ChuongTrinhUuDai, NhatKyGuiHDCS
from django.http import JsonResponse, Http404
from django.contrib.auth.models import User
from customers.models import KhachHang
from bookings.models import LichHen, PhanCongLichHen
from .models import HuongDanChamSoc


def is_staff(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


# =====================================================================
# 1. TRUNG TÂM THÔNG BÁO CỦA KHÁCH HÀNG & HỆ THỐNG
# =====================================================================
@login_required(login_url='/accounts/dang_nhap/')
def danh_sach_thong_bao(request):
    """
    Trang Trung tâm thông báo của khách hàng (Truy vấn chuẩn xác theo KhachHang instance)
    """
    # Lấy chính xác đối tượng KhachHang tương ứng với tài khoản đang đăng nhập
    khach_hang = KhachHang.objects.filter(
        Q(ma_tk__user=request.user) |
        Q(ma_tk__so_dien_thoai=request.user.username)
    ).first()

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


@login_required(login_url='/accounts/dang_nhap/')
def danh_dau_da_doc(request, ma_tbkh):
    """
    Đánh dấu thông báo là đã đọc một cách an toàn
    """
    khach_hang = KhachHang.objects.filter(
        Q(ma_tk__user=request.user) |
        Q(ma_tk__so_dien_thoai=request.user.username)
    ).first()

    if khach_hang:
        tb = get_object_or_404(
            ThongBaoKhachHang,
            Q(ma_tbkh=ma_tbkh) & (Q(ma_kh=khach_hang) | Q(ma_kh_id=khach_hang.pk))
        )
        tb.trang_thai_gui = 'Đã đọc'
        tb.save()

    return redirect('notifications:danh_sach_thong_bao')


# =====================================================================
# 2. MODULE ƯU ĐÃI (PROMOTIONS)
# =====================================================================

def danh_sach_uu_dai(request):
    promotions = ChuongTrinhUuDai.objects.filter(
        trang_thai='Đang áp dụng',
        gia_tri_uu_dai__gt=0
    ).exclude(
        ten_chuong_trinh__isnull=True
    ).order_by('-pk')

    context = {
        'promotions': promotions,
        'danh_sach': promotions,
    }
    return render(request, 'notifications/danh_sach_uu_dai.html', context)


def chi_tiet_uu_dai(request, promo_code):
    promo = get_object_or_404(ChuongTrinhUuDai, pk=promo_code)
    context = {
        'promo': promo,
    }
    return render(request, 'notifications/chi_tiet_uu_dai.html', context)


@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
def admin_promotion_list(request):
    ds_uu_dai = ChuongTrinhUuDai.objects.all().order_by('-pk')
    dang_ap_dung_count = ds_uu_dai.filter(trang_thai='Đang áp dụng').count()
    sap_dien_ra_count = ds_uu_dai.filter(trang_thai='Sắp diễn ra').count()

    context = {
        'ds_uu_dai': ds_uu_dai,
        'dang_ap_dung_count': dang_ap_dung_count,
        'sap_dien_ra_count': sap_dien_ra_count,
        'promotions': ds_uu_dai,
    }
    return render(request, 'notifications/admin_promotion_list.html', context)


@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
@require_POST
def api_them_hoac_sua_uu_dai(request):
    try:
        pk = request.POST.get('id', '').strip()
        tieu_de = request.POST.get('tieu_de', '').strip()
        mo_ta = request.POST.get('mo_ta', '').strip()
        ngay_bat_dau_str = request.POST.get('ngay_bat_dau')
        ngay_ket_thuc_str = request.POST.get('ngay_ket_thuc')

        hom_nay = date.today()
        ngay_bd = datetime.strptime(ngay_bat_dau_str, '%Y-%m-%d').date() if ngay_bat_dau_str else hom_nay
        ngay_kt = datetime.strptime(ngay_ket_thuc_str, '%Y-%m-%d').date() if ngay_ket_thuc_str else hom_nay

        if ngay_kt < hom_nay:
            trang_thai = 'Đã kết thúc'
        elif ngay_bd > hom_nay:
            trang_thai = 'Sắp diễn ra'
        else:
            trang_thai = 'Đang áp dụng'

        gia_tri = float(request.POST.get('gia_tri_uu_dai', 0) or 0)
        gia_goc = float(request.POST.get('gia_goc', 0) or 0)
        thoi_luong = request.POST.get('thoi_luong', '90 phút').strip()
        doi_tuong = request.POST.get('doi_tuong_ap_dung', 'Tất cả khách hàng').strip()
        dia_diem = request.POST.get('dia_diem_ap_dung', 'Charm Grand Spa & Wellness').strip()
        quyen_loi = request.POST.get('quyen_loi', '').strip()
        dieu_kien = request.POST.get('dieu_kien', '').strip()
        hinh_anh = request.POST.get('hinh_anh', '').strip()

        if not tieu_de:
            return JsonResponse({'success': False, 'error': 'Tên chương trình không được để trống!'})

        if pk:
            uu_dai = get_object_or_404(ChuongTrinhUuDai, pk=pk)
            uu_dai.ten_chuong_trinh = tieu_de
            uu_dai.mo_ta = mo_ta
            if ngay_bat_dau_str: uu_dai.ngay_bat_dau = ngay_bd
            if ngay_ket_thuc_str: uu_dai.ngay_ket_thuc = ngay_kt
            uu_dai.gia_tri_uu_dai = gia_tri
            uu_dai.gia_goc = gia_goc
            uu_dai.thoi_luong = thoi_luong
            uu_dai.doi_tuong_ap_dung = doi_tuong
            uu_dai.dia_diem_ap_dung = dia_diem
            uu_dai.quyen_loi = quyen_loi
            uu_dai.dieu_kien = dieu_kien
            uu_dai.trang_thai = trang_thai
            if hinh_anh: uu_dai.hinh_anh = hinh_anh
            uu_dai.save()
            msg = "Cập nhật thành công!"
        else:
            count = ChuongTrinhUuDai.objects.count() + 1
            ma_moi = f"CTUD{count:03d}"
            ChuongTrinhUuDai.objects.create(
                ma_ctud=ma_moi,
                ten_chuong_trinh=tieu_de,
                mo_ta=mo_ta,
                ngay_bat_dau=ngay_bd,
                ngay_ket_thuc=ngay_kt,
                gia_tri_uu_dai=gia_tri,
                gia_goc=gia_goc,
                thoi_luong=thoi_luong,
                doi_tuong_ap_dung=doi_tuong,
                dia_diem_ap_dung=dia_diem,
                quyen_loi=quyen_loi,
                dieu_kien=dieu_kien,
                trang_thai=trang_thai,
                hinh_anh=hinh_anh
            )
            msg = "Thêm mới thành công!"

        return JsonResponse({'success': True, 'message': msg})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
@require_POST
def api_gui_thong_bao_uu_dai(request):
    """
    API xử lý gửi thông báo ưu đãi trực tiếp đến đối tượng KhachHang chuẩn xác 100%
    """
    try:
        promo_id = (request.POST.get('promo_id') or '').strip()
        if not promo_id:
            return JsonResponse({'success': False, 'error': 'Thiếu mã chương trình ưu đãi.'}, status=400)

        promo = get_object_or_404(ChuongTrinhUuDai, pk=promo_id)
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
                'error': 'Tai khoan Admin chua co ho so TaiKhoan.'
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
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
def get_promotion_detail(request, ma_ctud):
    promo = get_object_or_404(ChuongTrinhUuDai, pk=ma_ctud)
    data = {
        'ma_ctud': getattr(promo, 'ma_ctud', str(promo.pk)),
        'ten_chuong_trinh': getattr(promo, 'ten_chuong_trinh', ''),
    }
    return JsonResponse(data)


@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
def xoa_uu_dai(request, ma_ctud):
    promo = get_object_or_404(ChuongTrinhUuDai, pk=ma_ctud)
    promo.delete()
    return redirect('notifications:admin_promotion_list')


@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
def them_uu_dai(request):
    return redirect('notifications:admin_promotion_list')


@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
def chinh_sua_uu_dai(request, ma_ctud):
    return redirect('notifications:admin_promotion_list')


# =====================================================================
# 3. MODULE CHĂM SÓC SAU LIỆU TRÌNH (AFTERCARE)
# =====================================================================
@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
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


@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
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
            'error': 'Admin chưa có hồ sơ TaiKhoan, không thể xác định người gửi.'
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


@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
def get_hdcs_detail(request, id):
    record = get_object_or_404(NhatKyGuiHDCS, pk=id)
    return JsonResponse({
        'id': record.pk,
        'noi_dung': record.noi_dung_gui or '',
        'trang_thai': record.trang_thai,
        'thoi_gian_gui': timezone.localtime(record.thoi_gian_gui).strftime('%d/%m/%Y %H:%M')
        if record.thoi_gian_gui else None,
    })


@login_required(login_url='/accounts/dang_nhap/')
def customer_aftercare_detail(request, id):
    record = get_object_or_404(NhatKyGuiHDCS, pk=id)
    context = {
        'record': record,
    }
    return render(request, 'notifications/customer_aftercare_detail.html', context)


@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
def lich_hen_chu_ky_cham_soc(request):
    context = {}
    return render(request, 'notifications/lich_hen_chu_ky_cham_soc.html', context)


@login_required(login_url='/accounts/dang_nhap/')
def dat_lich_tai_hen_nhanh(request):
    return redirect('notifications:danh_sach_thong_bao')
