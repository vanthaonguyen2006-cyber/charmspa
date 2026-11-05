from datetime import date
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from .models import ThongBaoKhachHang, ChuongTrinhUuDai, NhatKyGuiHDCS
from django.http import JsonResponse, Http404
from django.contrib.auth.models import User


def is_staff(user):
    return user.is_authenticated and (user.is_staff or getattr(user, 'vai_tro', '') in ['Staff', 'Admin'])


# =====================================================================
# 1. TRUNG TÂM THÔNG BÁO CỦA KHÁCH HÀNG & HỆ THỐNG
# =====================================================================
@login_required(login_url='/accounts/dang_nhap/')
def danh_sach_thong_bao(request):
    """
    Trang Trung tâm thông báo của hệ thống
    """
    thong_bao_list = ThongBaoKhachHang.objects.filter(ma_kh=request.user).order_by('-thoi_gian_gui')
    context = {
        'thong_bao_list': thong_bao_list,
    }
    return render(request, 'notifications/danh_sach_thong_bao.html', context)


@login_required(login_url='/accounts/dang_nhap/')
def danh_dau_da_doc(request, ma_tbkh):
    tb = get_object_or_404(ThongBaoKhachHang, ma_tbkh=ma_tbkh, ma_kh=request.user)
    tb.trang_thai_gui = 'Đã đọc'
    tb.save()
    return redirect('notifications:danh_sach_thong_bao')


# =====================================================================
# 2. MODULE ƯU ĐÃI (PROMOTIONS)
# =====================================================================

def danh_sach_uu_dai(request):
    """
    Trang danh sách ưu đãi cho khách hàng
    Chỉ hiển thị các chương trình đang áp dụng VÀ đã có đầy đủ thông tin (giá trị ưu đãi lớn hơn 0)
    """
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
    """
    Trang chi tiết ưu đãi
    """
    promo = get_object_or_404(ChuongTrinhUuDai, pk=promo_code)
    context = {
        'promo': promo,
    }
    return render(request, 'notifications/chi_tiet_uu_dai.html', context)


# --- Admin Promotions (Quản lý ưu đãi phía Staff/Admin) ---
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
        'promotions': ds_uu_dai,  # Giữ tương thích nếu template cũ dùng biến này
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
        ngay_bat_dau = request.POST.get('ngay_bat_dau')
        ngay_ket_thuc = request.POST.get('ngay_ket_thuc')
        gia_tri = float(request.POST.get('gia_tri_uu_dai', 0) or 0)
        gia_goc = float(request.POST.get('gia_goc', 0) or 0)
        thoi_luong = request.POST.get('thoi_luong', '90 phút').strip()
        doi_tuong = request.POST.get('doi_tuong_ap_dung', 'Tất cả khách hàng').strip()
        dia_diem = request.POST.get('dia_diem_ap_dung', 'Charm Grand Spa & Wellness').strip()
        quyen_loi = request.POST.get('quyen_loi', '').strip()
        dieu_kien = request.POST.get('dieu_kien', '').strip()
        trang_thai = request.POST.get('trang_thai', 'Đang áp dụng')
        hinh_anh = request.POST.get('hinh_anh', '').strip()

        if not tieu_de:
            return JsonResponse({'success': False, 'error': 'Tên chương trình không được để trống!'})

        if pk:
            uu_dai = get_object_or_404(ChuongTrinhUuDai, pk=pk)
            uu_dai.ten_chuong_trinh = tieu_de
            uu_dai.mo_ta = mo_ta
            if ngay_bat_dau: uu_dai.ngay_bat_dau = ngay_bat_dau
            if ngay_ket_thuc: uu_dai.ngay_ket_thuc = ngay_ket_thuc
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
                ngay_bat_dau=ngay_bat_dau or date.today(),
                ngay_ket_thuc=ngay_ket_thuc or date.today(),
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
    API xử lý gửi thông báo ưu đãi đến khách hàng theo các hạng thành viên (Đồng, Bạc, Vàng, Kim Cương...)
    """
    try:
        promo_id = request.POST.get('promo_id')
        doi_tuong = request.POST.get('doi_tuong', 'tat_ca')

        promo = get_object_or_404(ChuongTrinhUuDai, pk=promo_id)

        # Lọc danh sách tài khoản khách hàng theo phân hạng
        if doi_tuong == 'tat_ca':
            khach_hang_list = User.objects.filter(is_staff=False, is_superuser=False)
        elif doi_tuong in ['dong', 'bac', 'vang', 'kim_cuong', 'thanh_vien_moi']:
            # Có thể lọc mở rộng theo quan hệ hồ sơ khách hàng nếu có, tạm thời lấy toàn bộ user khách hàng
            khach_hang_list = User.objects.filter(is_staff=False, is_superuser=False)
        else:
            khach_hang_list = User.objects.filter(is_staff=False, is_superuser=False)

        tieu_de = f"Ưu đãi đặc quyền: {promo.ten_chuong_trinh}"
        noi_dung = f"Nhận ngay ưu đãi trị giá {promo.gia_tri_uu_dai:,.0f}đ khi trải nghiệm tại Charm Grand Spa."
        duong_dan = f"/notifications/promotions/detail/{promo.pk}/"

        # Tạo bản ghi thông báo vào bảng ThongBaoKhachHang cho từng khách hàng
        for kh in khach_hang_list:
            # Kiểm tra xem model ThongBaoKhachHang có các trường tương ứng hay không
            try:
                # Tạo mã thông báo tự động tăng hoặc duy nhất
                count_tb = ThongBaoKhachHang.objects.count() + 1
                ma_tb = f"TB{count_tb:04d}"

                ThongBaoKhachHang.objects.create(
                    ma_tbkh=ma_tb,
                    ma_kh=kh,
                    tieu_de=tieu_de,
                    noi_dung=noi_dung,
                    trang_thai_gui='Chưa đọc'
                )
            except Exception:
                pass

        return JsonResponse({'success': True, 'message': 'Gửi thông báo ưu đãi thành công!'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


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
    """
    Hàm phụ trợ hỗ trợ URL them_uu_dai
    """
    return redirect('notifications:admin_promotion_list')


@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
def chinh_sua_uu_dai(request, ma_ctud):
    """
    Hàm phụ trợ hỗ trợ URL chinh_sua_uu_dai
    """
    return redirect('notifications:admin_promotion_list')


# =====================================================================
# 3. MODULE CHĂM SÓC SAU LIỆU TRÌNH (AFTERCARE)
# =====================================================================
@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
def cham_soc_sau_lieu_trinh(request):
    records = NhatKyGuiHDCS.objects.all()
    context = {
        'records': records,
    }
    return render(request, 'notifications/cham_soc_sau_lieu_trinh.html', context)


@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
def gui_hdcs_action(request, id):
    record = get_object_or_404(NhatKyGuiHDCS, pk=id)
    # Xử lý gửi hướng dẫn chăm sóc
    return redirect('notifications:cham_soc_sau_lieu_trinh')


@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
def get_hdcs_detail(request, id):
    record = get_object_or_404(NhatKyGuiHDCS, pk=id)
    data = {
        'id': record.id,
        'noi_dung': getattr(record, 'noi_dung', ''),
    }
    return JsonResponse(data)


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