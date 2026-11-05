import csv
import json
import datetime
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.text import slugify
from customers.forms import (
    ThemNhanVienForm,
    ChinhSuaTaiKhoanForm,
    ThemKhachHangForm,
    ChinhSuaHoSoKhachHangForm,
)

from customers.models import KhachHang, HangThanhVien
from accounts.models import TaiKhoan, NhanVien, LichSuTaiKhoan
from customers.forms import ThemNhanVienForm, ChinhSuaTaiKhoanForm
from services.models import DichVu, DichVuDaSuDung
from django.conf import settings
User = get_user_model()


# =========================================================================
# CÁC HÀM KIỂM TRA PHÂN QUYỀN CHUẨN (is_staff & is_superuser)
# =========================================================================
def is_admin_user(user):
    """Chỉ Quản trị viên tối cao mới có quyền (is_superuser = True)"""
    return user.is_authenticated and user.is_superuser


def is_staff_user(user):
    """Nhân viên hoặc Quản trị viên đều vào được (is_staff = True)"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def is_customer_user(user):
    """Khách hàng thông thường (Không phải staff, không phải superuser)"""
    return user.is_authenticated and not user.is_staff and not user.is_superuser


def _format_number_vn(value):
    """Định dạng số theo kiểu Việt Nam: 1325 -> 1.325."""
    return f"{value:,}".replace(",", ".")


def _get_customer_initials(full_name):
    """Lấy chữ cái đầu của hai từ cuối, ví dụ Nguyễn Minh Anh -> MA."""
    words = (full_name or "").strip().split()
    if not words:
        return "KH"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[-2][0] + words[-1][0]).upper()


# =========================================================================
# XEM VÀ CHỈNH SỬA HỒ SƠ CÁ NHÂN (DÀNH CHO KHÁCH HÀNG)
# =========================================================================
@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_customer_user, login_url='/home/staff/')
def customer_profile_view(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect('/home/staff/')

    tai_khoan = getattr(request.user, 'thong_tin_tai_khoan', None)

    khach_hang = None
    if tai_khoan:
        khach_hang = getattr(tai_khoan, 'ho_so_khach_hang', None)
    if not khach_hang:
        khach_hang = KhachHang.objects.filter(ma_tk__user=request.user).first()

    # 3. Lấy lịch sử sử dụng dịch vụ của chính khách hàng đang đăng nhập
    lich_su_dich_vu = []
    tong_so_dich_vu = 0
    if khach_hang and hasattr(khach_hang, 'ma_kh'):
        try:
            from services.models import DichVuDaSuDung
            qs = (
                DichVuDaSuDung.objects.filter(ma_kh=khach_hang)
                .select_related('ma_dv', 'ma_nv')
                .order_by('-ngay_su_dung')
            )
            tong_so_dich_vu = qs.count()
            lich_su_dich_vu = list(qs)
        except Exception as e:
            print(f"Lỗi truy vấn lịch sử dịch vụ khách hàng: {e}")
            lich_su_dich_vu = []
            tong_so_dich_vu = 0

    is_editing = request.GET.get('edit') == 'true' or request.method == 'POST'

    if request.method == 'POST':
        form = ChinhSuaHoSoKhachHangForm(
            request.POST,
            current_user=request.user,
            current_tai_khoan=tai_khoan
        )
        if form.is_valid():
            cleaned = form.cleaned_data
            try:
                with transaction.atomic():
                    # 1. Cập nhật Username và Email cho Django User
                    user = request.user
                    user.username = cleaned['username']
                    user.email = cleaned['email']
                    user.save(update_fields=['username', 'email'])

                    # 2. Cập nhật thông tin KhachHang (không sửa ma_kh, diem_tich_luy_kh, ma_tv)
                    if khach_hang:
                        khach_hang.ho_ten = cleaned['ho_ten']
                        khach_hang.ngay_sinh = cleaned['ngay_sinh']
                        khach_hang.gioi_tinh = cleaned['gioi_tinh'] or None
                        khach_hang.save(update_fields=['ho_ten', 'ngay_sinh', 'gioi_tinh'])

                    # 3. Cập nhật số điện thoại cho TaiKhoan
                    if tai_khoan:
                        tai_khoan.so_dien_thoai = cleaned['so_dien_thoai']
                        tai_khoan.save(update_fields=['so_dien_thoai'])

                messages.success(request, 'Cập nhật hồ sơ cá nhân thành công.')
                return redirect('customer_profile')

            except Exception as e:
                form.add_error(None, f"Không thể lưu thay đổi: {e}")
                is_editing = True
        else:
            is_editing = True
    else:
        initial_data = {
            'ho_ten': khach_hang.ho_ten if khach_hang else (request.user.get_full_name() or request.user.username),
            'username': request.user.username,
            'so_dien_thoai': tai_khoan.so_dien_thoai if tai_khoan else '',
            'email': request.user.email or '',
            'ngay_sinh': khach_hang.ngay_sinh if khach_hang else None,
            'gioi_tinh': khach_hang.gioi_tinh if khach_hang else '',
        }
        form = ChinhSuaHoSoKhachHangForm(
            initial=initial_data,
            current_user=request.user,
            current_tai_khoan=tai_khoan
        )

    if not khach_hang:
        class TempKhachHang:
            ho_ten = request.user.get_full_name() or request.user.username
            ngay_sinh = None
            gioi_tinh = "Nam"
            ma_kh = "Chưa có mã"
            diem_tich_luy_kh = 0
            ma_tv = None

            @property
            def ma_tk(self):
                class DummyTk:
                    so_dien_thoai = tai_khoan.so_dien_thoai if tai_khoan else ""
                return DummyTk()

        khach_hang = TempKhachHang()

    viewed_services = request.session.get('viewed_services', [])

    context = {
        'khach_hang': khach_hang,
        'tai_khoan': tai_khoan,
        'lich_su_dich_vu': lich_su_dich_vu,
        'tong_so_dich_vu': tong_so_dich_vu,
        'viewed_services': viewed_services,
        'is_editing': is_editing,
        'form': form,
    }

    return render(request, 'customer/customer_profile.html', context)

# =========================================================================
# KHÁCH HÀNG TỰ KHÓA TÀI KHOẢN
# =========================================================================
@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_customer_user, login_url='/home/staff/')
def customer_lock_account_view(request):
    """
    Cho phép khách hàng chủ động yêu cầu khóa tài khoản của chính mình:
- Ghi nhận lý do vào bảng LICH_SU_TAI_KHOAN.

- Chuyển cờ is_active của User sang False.

- Đăng xuất phiên làm việc hiện tại và điều hướng tới trang thông báo khóa.

    """
    if request.method == 'POST':
        ly_do_chon = request.POST.get('ly_do', '').strip()
        ly_do_khac = request.POST.get('ly_do_khac', '').strip()
        ly_do_chi_tiet = ly_do_khac if ly_do_chon == 'Lý do khác' else ly_do_chon

        user = request.user
        tai_khoan_hien_tai = getattr(user, 'thong_tin_tai_khoan', None)

        if tai_khoan_hien_tai:
            count_ls = LichSuTaiKhoan.objects.count() + 1
            ma_ls_str = f"LS{count_ls:03d}"

            LichSuTaiKhoan.objects.create(
                ma_ls=ma_ls_str,
                ma_tk=tai_khoan_hien_tai,
                ma_tk_thuc_hien=tai_khoan_hien_tai,
                hanh_dong="Khóa",
                ly_do=ly_do_chi_tiet or "Khách hàng tự khóa tài khoản cá nhân."
            )

        # Vô hiệu hóa tài khoản Django User
        user.is_active = False
        user.save(update_fields=['is_active'])

        # Đăng xuất tài khoản ngay lập tức
        logout(request)

        return redirect('account_locked')

    return redirect('customer_profile')


def account_locked_view(request):
    """Hiển thị giao diện thông báo khóa tài khoản thành công"""
    return render(request, 'customer/account_locked.html')


# =========================================================================
# QUẢN LÝ DANH SÁCH KHÁCH HÀNG (DÀNH CHO NHÂN VIÊN / ADMIN)
# =========================================================================
@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff_user, login_url='/home/customer/')
def staff_customer_list_view(request):
    today = timezone.localdate()

    query = request.GET.get('q', '').strip()
    hang = request.GET.get('hang', '').strip()
    trang_thai = request.GET.get('trang_thai', '').strip()
    ngay_tham_gia = request.GET.get('ngay_tham_gia', '').strip()

    # Chuẩn hóa trạng thái: loại bỏ hoàn toàn 'chua_tai_khoan', chỉ nhận 'hoat_dong' hoặc 'da_khoa'
    if trang_thai not in ['hoat_dong', 'da_khoa']:
        trang_thai = ''

    # Danh sách các mốc thời gian lọc ngày tham gia hợp lệ
    valid_ngay_tham_gia = ['1_tuan', '2_tuan', '1_thang', '30_ngay', '2_thang', '60_ngay', 'thang_nay']
    if ngay_tham_gia not in valid_ngay_tham_gia:
        ngay_tham_gia = ''

    # 2. Lấy danh sách khách hàng và các quan hệ liên quan
    khach_hang_list = KhachHang.objects.select_related(
        'ma_tk',
        'ma_tk__user',
        'ma_tv',
    ).all()

    # 3. Tìm kiếm theo mã KH, họ tên, SĐT, email
    if query:
        khach_hang_list = khach_hang_list.filter(
            Q(ma_kh__icontains=query)
            | Q(ho_ten__icontains=query)
            | Q(ma_tk__so_dien_thoai__icontains=query)
            | Q(ma_tk__user__email__icontains=query)
        )

    # 4. Lọc hạng thành viên
    if hang:
        khach_hang_list = khach_hang_list.filter(ma_tv_id=hang)

    # 5. Lọc trạng thái tài khoản (chỉ lọc 'hoat_dong' hoặc 'da_khoa')
    if trang_thai == 'hoat_dong':
        khach_hang_list = khach_hang_list.filter(
            ma_tk__user__is_active=True
        )
    elif trang_thai == 'da_khoa':
        khach_hang_list = khach_hang_list.filter(
            ma_tk__user__is_active=False
        )

    # 6. Lọc ngày tham gia dựa trên ngày tạo tài khoản (TaiKhoan.ngay_tao)
    dau_thang = today.replace(day=1)

    if ngay_tham_gia == '1_tuan':
        # 1 tuần gần đây: 7 ngày gần nhất
        tu_ngay = today - timedelta(days=7)
        khach_hang_list = khach_hang_list.filter(
            ma_tk__ngay_tao__date__gte=tu_ngay,
            ma_tk__ngay_tao__date__lte=today,
        )
    elif ngay_tham_gia == '2_tuan':
        # 2 tuần gần đây: 14 ngày gần nhất
        tu_ngay = today - timedelta(days=14)
        khach_hang_list = khach_hang_list.filter(
            ma_tk__ngay_tao__date__gte=tu_ngay,
            ma_tk__ngay_tao__date__lte=today,
        )
    elif ngay_tham_gia in ['1_thang', '30_ngay']:
        # 1 tháng gần đây: 30 ngày gần nhất
        tu_ngay = today - timedelta(days=30)
        khach_hang_list = khach_hang_list.filter(
            ma_tk__ngay_tao__date__gte=tu_ngay,
            ma_tk__ngay_tao__date__lte=today,
        )
    elif ngay_tham_gia in ['2_thang', '60_ngay']:
        # 2 tháng gần đây: 60 ngày gần nhất
        tu_ngay = today - timedelta(days=60)
        khach_hang_list = khach_hang_list.filter(
            ma_tk__ngay_tao__date__gte=tu_ngay,
            ma_tk__ngay_tao__date__lte=today,
        )
    elif ngay_tham_gia == 'thang_nay':
        # Tháng này: từ đầu tháng hiện tại đến ngày hôm nay
        khach_hang_list = khach_hang_list.filter(
            ma_tk__ngay_tao__date__gte=dau_thang,
            ma_tk__ngay_tao__date__lte=today,
        )

    # 7. Thống kê tổng quan
    tong_khach_hang = KhachHang.objects.count()

    khach_vip = KhachHang.objects.filter(
        Q(ma_tv__ten_hang__icontains='Vàng')
        | Q(ma_tv__ten_hang__icontains='Kim cương')
    ).count()

    # Đếm khách hàng có tài khoản được tạo trong tháng này
    khach_moi_thang_nay = KhachHang.objects.filter(
        ma_tk__ngay_tao__date__gte=dau_thang,
        ma_tk__ngay_tao__date__lte=today,
    ).count()

    # 8. Xuất CSV theo điều kiện lọc hiện tại
    if request.GET.get('export') == 'csv':
        response = HttpResponse(
            content_type='text/csv; charset=utf-8-sig'
        )
        response['Content-Disposition'] = (
            'attachment; filename="danh_sach_khach_hang.csv"'
        )

        writer = csv.writer(response)
        writer.writerow([
            'Mã khách hàng',
            'Họ và tên',
            'Số điện thoại',
            'Email',
            'Điểm tích lũy',
            'Hạng thành viên',
            'Ngày tham gia',
            'Trạng thái tài khoản',
        ])

        for kh in khach_hang_list:
            tai_khoan = kh.ma_tk
            user = tai_khoan.user if tai_khoan else None

            ngay_tao = tai_khoan.ngay_tao if tai_khoan else None

            ngay_tao_text = (
                timezone.localtime(ngay_tao).strftime('%d/%m/%Y')
                if ngay_tao else ''
            )

            if not tai_khoan:
                trang_thai_text = 'Chưa có tài khoản'
            elif user and user.is_active:
                trang_thai_text = 'Đang hoạt động'
            else:
                trang_thai_text = 'Đã khóa'

            writer.writerow([
                kh.ma_kh,
                kh.ho_ten,
                tai_khoan.so_dien_thoai if tai_khoan else '',
                user.email if user else '',
                kh.diem_tich_luy_kh,
                kh.ma_tv.ten_hang if kh.ma_tv else 'Thành viên mới',
                ngay_tao_text,
                trang_thai_text,
            ])

        return response

    # 9. Phân trang: 6 khách hàng/trang
    paginator = Paginator(khach_hang_list, 6)
    page_obj = paginator.get_page(request.GET.get('page'))

    for kh in page_obj.object_list:
        kh.avatar_initials = _get_customer_initials(kh.ho_ten)
        kh.tier_slug = (
            slugify(kh.ma_tv.ten_hang)
            if kh.ma_tv else 'moi'
        )
        kh.points_display = _format_number_vn(
            kh.diem_tich_luy_kh or 0
        )

    # 11. Giữ bộ lọc khi chuyển trang (làm sạch không để tham số cũ xuất hiện trên URL)
    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_params.pop('export', None)
    if 'trang_thai' in query_params and query_params['trang_thai'] not in ['hoat_dong', 'da_khoa']:
        query_params.pop('trang_thai', None)
    if 'ngay_tham_gia' in query_params and query_params['ngay_tham_gia'] not in valid_ngay_tham_gia:
        query_params.pop('ngay_tham_gia', None)
    pagination_query = query_params.urlencode()

    export_params = request.GET.copy()
    export_params.pop('page', None)
    export_params['export'] = 'csv'
    if 'trang_thai' in export_params and export_params['trang_thai'] not in ['hoat_dong', 'da_khoa']:
        export_params.pop('trang_thai', None)
    if 'ngay_tham_gia' in export_params and export_params['ngay_tham_gia'] not in valid_ngay_tham_gia:
        export_params.pop('ngay_tham_gia', None)
    export_url = '?' + export_params.urlencode()

    # 12. Tạo danh sách số trang
    current_page = page_obj.number
    total_pages = paginator.num_pages
    page_items = []

    if total_pages <= 5:
        for number in range(1, total_pages + 1):
            page_items.append({
                'number': number,
                'current': number == current_page,
            })
    else:
        page_items.append({
            'number': 1,
            'current': current_page == 1,
        })

        start_page = max(2, current_page - 1)
        end_page = min(total_pages - 1, current_page + 1)

        if start_page > 2:
            page_items.append({'ellipsis': True})

        for number in range(start_page, end_page + 1):
            page_items.append({
                'number': number,
                'current': number == current_page,
            })

        if end_page < total_pages - 1:
            page_items.append({'ellipsis': True})

        page_items.append({
            'number': total_pages,
            'current': current_page == total_pages,
        })

    # 13. Truyền dữ liệu sang template
    context = {
        'khach_hang_list': page_obj.object_list,
        'page_obj': page_obj,

        'hang_list': HangThanhVien.objects.order_by(
            'diem_toi_thieu'
        ),

        'tong_khach_hang_display': _format_number_vn(
            tong_khach_hang
        ),
        'khach_vip_display': _format_number_vn(khach_vip),
        'khach_moi_thang_nay_display': _format_number_vn(
            khach_moi_thang_nay
        ),

        'query': query,
        'hang_selected': hang,
        'trang_thai_selected': trang_thai,
        'ngay_tham_gia_selected': ngay_tham_gia,

        'pagination_query': pagination_query,
        'page_items': page_items,
        'export_url': export_url,

        'showing_start': (
            page_obj.start_index() if paginator.count else 0
        ),
        'showing_end': (
            page_obj.end_index() if paginator.count else 0
        ),
        'filtered_count_display': _format_number_vn(
            paginator.count
        ),
    }

    return render(
        request,
        'customer/staff_customer_list.html',
        context,
    )

# =========================================================================
# XEM CHI TIẾT TÀI KHOẢN VÀ LỊCH SỬ KHÓA / MỞ KHÓA (CHỈ ADMIN)
# =========================================================================
@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff_user, login_url='/home/customer/')
def staff_account_detail_view(request, ma_tk):
    if not is_admin_user(request.user):
        raise PermissionDenied("Chức năng Quản trị người dùng chỉ dành cho Quản trị viên.")

    tai_khoan = get_object_or_404(
        TaiKhoan.objects.select_related('user', 'ho_so_nhan_vien', 'ho_so_khach_hang'),
        ma_tk=ma_tk
    )
    user_obj = tai_khoan.user

    # Xác định họ và tên hiển thị từ hồ sơ liên kết
    nhan_vien = getattr(tai_khoan, 'ho_so_nhan_vien', None)
    khach_hang = getattr(tai_khoan, 'ho_so_khach_hang', None)
    if nhan_vien and nhan_vien.ho_ten:
        ho_ten = nhan_vien.ho_ten
    elif khach_hang and khach_hang.ho_ten:
        ho_ten = khach_hang.ho_ten
    elif user_obj:
        ho_ten = user_obj.get_full_name() or user_obj.username
    else:
        ho_ten = tai_khoan.ma_tk

    # Truy vấn toàn bộ lịch sử khóa và mở khóa của tài khoản đang xem
    lich_su_list = (
        LichSuTaiKhoan.objects.filter(ma_tk=tai_khoan)
        .select_related(
            'ma_tk_thuc_hien',
            'ma_tk_thuc_hien__user',
            'ma_tk_thuc_hien__ho_so_nhan_vien',
            'ma_tk_thuc_hien__ho_so_khach_hang'
        )
        .order_by('-thoi_gian')
    )

    for ls in lich_su_list:
        th = ls.ma_tk_thuc_hien
        if th:
            nv_th = getattr(th, 'ho_so_nhan_vien', None)
            kh_th = getattr(th, 'ho_so_khach_hang', None)
            if nv_th and nv_th.ho_ten:
                ls.ten_nguoi_thuc_hien = nv_th.ho_ten
            elif kh_th and kh_th.ho_ten:
                ls.ten_nguoi_thuc_hien = kh_th.ho_ten
            elif th.user:
                ls.ten_nguoi_thuc_hien = th.user.get_full_name() or th.user.username
            else:
                ls.ten_nguoi_thuc_hien = th.ma_tk
        else:
            ls.ten_nguoi_thuc_hien = "Hệ thống"

    avatar_initials = user_obj.username[:2].upper() if (user_obj and user_obj.username) else "TK"

    context = {
        'tai_khoan': tai_khoan,
        'user_obj': user_obj,
        'ho_ten': ho_ten,
        'avatar_initials': avatar_initials,
        'lich_su_list': lich_su_list,
    }
    return render(request, 'customer/staff_account_detail.html', context)
# =========================================================================
# XEM VÀ CHỈNH SỬA HỒ SƠ KHÁCH HÀNG (DÀNH CHO NHÂN VIÊN)
# =========================================================================
@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff_user, login_url='/home/customer/')
def staff_customer_detail_view(request, ma_kh):
    khach_hang = get_object_or_404(
        KhachHang.objects.select_related(
            'ma_tk',
            'ma_tk__user',
            'ma_tv',
        ),
        ma_kh=ma_kh,
    )

    tai_khoan = khach_hang.ma_tk
    user = tai_khoan.user if tai_khoan else None

    if not tai_khoan:
        trang_thai_tai_khoan = 'Chưa có tài khoản'
        trang_thai_class = 'neutral'
    elif user and user.is_active:
        trang_thai_tai_khoan = 'Đang hoạt động'
        trang_thai_class = 'success'
    else:
        trang_thai_tai_khoan = 'Đã khóa'
        trang_thai_class = 'danger'

    is_editing = (
        request.GET.get('edit') == '1'
        or request.GET.get('edit') == 'true'
        or request.method == 'POST'
    )

    if request.method == 'POST':
        form = ChinhSuaHoSoKhachHangForm(
            request.POST,
            current_user=user,
            current_tai_khoan=tai_khoan
        )
        if form.is_valid():
            cleaned = form.cleaned_data
            try:
                with transaction.atomic():
                    # 1. Cập nhật thông tin KhachHang (không sửa ma_kh, diem_tich_luy_kh, ma_tv)
                    khach_hang.ho_ten = cleaned['ho_ten']
                    khach_hang.ngay_sinh = cleaned['ngay_sinh']
                    khach_hang.gioi_tinh = cleaned['gioi_tinh'] or None
                    khach_hang.save(update_fields=['ho_ten', 'ngay_sinh', 'gioi_tinh'])

                    # 2. Cập nhật số điện thoại cho TaiKhoan
                    if tai_khoan:
                        tai_khoan.so_dien_thoai = cleaned['so_dien_thoai']
                        tai_khoan.save(update_fields=['so_dien_thoai'])

                    # 3. Cập nhật Username và Email cho Django User
                    if user:
                        user.username = cleaned['username']
                        user.email = cleaned['email']
                        user.save(update_fields=['username', 'email'])

                messages.success(
                    request,
                    'Cập nhật hồ sơ khách hàng thành công.'
                )
                return redirect(
                    'staff_customer_detail',
                    ma_kh=khach_hang.ma_kh,
                )

            except Exception as e:
                form.add_error(None, f'Không thể lưu thông tin: {e}')
                is_editing = True
        else:
            is_editing = True
    else:
        initial_data = {
            'ho_ten': khach_hang.ho_ten,
            'username': user.username if user else '',
            'so_dien_thoai': tai_khoan.so_dien_thoai if tai_khoan else '',
            'email': user.email if user else '',
            'ngay_sinh': khach_hang.ngay_sinh,
            'gioi_tinh': khach_hang.gioi_tinh or '',
        }
        form = ChinhSuaHoSoKhachHangForm(
            initial=initial_data,
            current_user=user,
            current_tai_khoan=tai_khoan
        )

    from services.models import DichVuDaSuDung

    danh_sach_su_dung = DichVuDaSuDung.objects.filter(
        ma_kh=khach_hang
    ).select_related('ma_dv', 'ma_nv').order_by('-ngay_su_dung')[:50]

    lich_su_dich_vu = []
    ty_le_giam_ap_dung = khach_hang.ma_tv.ty_le_giam_gia if khach_hang.ma_tv else Decimal('0.00')

    for sd in danh_sach_su_dung:
        gia_goc = sd.ma_dv.gia_dich_vu if sd.ma_dv else 0
        thanh_tien = float(gia_goc) * (1 - float(ty_le_giam_ap_dung) / 100) if gia_goc else None

        lich_su_dich_vu.append({
            'ma_sd': sd.ma_sd,
            'ngay': sd.ngay_su_dung,
            'dich_vu': sd.ma_dv.ten_dich_vu if sd.ma_dv else 'Dịch vụ đã sử dụng',
            'loai_dich_vu': sd.ma_dv.loai_dich_vu if sd.ma_dv else 'Dịch vụ chăm sóc',
            'mo_ta': sd.ma_dv.mo_ta if sd.ma_dv and sd.ma_dv.mo_ta else 'Không có mô tả chi tiết.',
            'thoi_luong': sd.ma_dv.thoi_luong if sd.ma_dv else 0,
            'nhan_vien': sd.ma_nv.ho_ten if sd.ma_nv else '—',
            'khach_hang': khach_hang.ho_ten,
            'gia_goc': gia_goc,
            'ty_le_giam_gia': ty_le_giam_ap_dung,
            'gia_tri': thanh_tien,
            'diem': sd.ma_dv.diem_tich_luy_dich_vu if sd.ma_dv else 0,
            'trang_thai': 'Đã hoàn thành',
        })

    so_luot_su_dung = len(lich_su_dich_vu)
    initials = _get_customer_initials(khach_hang.ho_ten)

    context = {
        'khach_hang': khach_hang,
        'tai_khoan': tai_khoan,
        'user': user,
        'ngay_tao': tai_khoan.ngay_tao if tai_khoan else None,
        'trang_thai_tai_khoan': trang_thai_tai_khoan,
        'trang_thai_class': trang_thai_class,
        'initials': initials,
        'lich_su_dich_vu': lich_su_dich_vu,
        'so_luot_su_dung': so_luot_su_dung,
        'is_editing': is_editing,
        'form': form,
    }

    return render(
        request,
        'customer/staff_customer_detail.html',
        context,
    )

# =========================================================================
# THÊM MỚI KHÁCH HÀNG (TRANG RIÊNG BIỆT)
# =========================================================================
@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff_user, login_url='/home/customer/')
def staff_customer_add_view(request):
    if request.method == 'POST':
        form = ThemKhachHangForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            ho_ten = cleaned['ho_ten']
            so_dien_thoai = cleaned['so_dien_thoai']
            email = cleaned['email']
            ngay_sinh = cleaned['ngay_sinh']
            gioi_tinh = cleaned['gioi_tinh']

            try:
                with transaction.atomic():
                    # Lấy hạng thành viên mặc định
                    hang_mac_dinh = HangThanhVien.objects.order_by(
                        'diem_toi_thieu', 'ma_tv'
                    ).first()
                    if hang_mac_dinh is None:
                        messages.error(
                            request,
                            'Chưa có hạng thành viên trong hệ thống. Không thể thêm khách hàng.'
                        )
                        return render(request, 'customer/staff_customer_add.html', {'form': form})

                    # 1. Tạo User Django cho khách hàng
                    username_moi = f'kh_{so_dien_thoai}'
                    if User.objects.filter(username=username_moi).exists():
                        form.add_error('so_dien_thoai', 'Tên đăng nhập theo số điện thoại này đã tồn tại.')
                        return render(request, 'customer/staff_customer_add.html', {'form': form})

                    user_moi = User(
                        username=username_moi,
                        email=email,
                    )
                    user_moi._so_dien_thoai_dang_ky = so_dien_thoai
                    user_moi.set_password('Password123@')
                    user_moi.save()

                    # 2. Lấy TaiKhoan vừa được Signal tạo tự động
                    tai_khoan_moi = TaiKhoan.objects.get(user=user_moi)

                    # 3. Sinh mã khách hàng tự động tăng (dạng KH-00001)
                    ma_kh_moi = None
                    for kh_cu in KhachHang.objects.filter(ma_kh__startswith='KH-').only('ma_kh'):
                        try:
                            so_thu_tu = int(kh_cu.ma_kh.split('-')[-1])
                            if ma_kh_moi is None or so_thu_tu > ma_kh_moi:
                                ma_kh_moi = so_thu_tu
                        except (ValueError, IndexError):
                            continue

                    ma_kh_moi = f'KH-{(ma_kh_moi or 0) + 1:05d}'

                    # 4. Tạo hồ sơ khách hàng
                    KhachHang.objects.create(
                        ma_kh=ma_kh_moi,
                        ma_tk=tai_khoan_moi,
                        ma_tv=hang_mac_dinh,
                        ho_ten=ho_ten,
                        ngay_sinh=ngay_sinh,
                        gioi_tinh=gioi_tinh,
                        diem_tich_luy_kh=0
                    )

                messages.success(request, f'Đã thêm khách hàng "{ho_ten}" thành công!')
                return redirect('staff_customer_list')

            except Exception as e:
                form.add_error(None, f"Lỗi khi lưu dữ liệu khách hàng: {e}")
                return render(request, 'customer/staff_customer_add.html', {'form': form})
        else:
            return render(request, 'customer/staff_customer_add.html', {'form': form})

    # GET: mở trang thêm mới với form rỗng
    form = ThemKhachHangForm()
    return render(request, 'customer/staff_customer_add.html', {'form': form})

# =========================================================================
# 1. QUẢN LÝ DANH SÁCH TÀI KHOẢN TOÀN HỆ THỐNG (CHỈ ADMIN)
# =========================================================================
@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff_user, login_url='/home/customer/')
def staff_account_list_view(request, add_staff_form=None, show_add_modal=False):
    if not is_admin_user(request.user):
        raise PermissionDenied("Chức năng Quản trị người dùng chỉ dành cho Quản trị viên.")

    # 1. Lấy điều kiện tìm kiếm và lọc
    query = request.GET.get('q', '').strip()
    vai_tro = request.GET.get('vai_tro', '').strip()
    trang_thai = request.GET.get('trang_thai', '').strip()
    ngay_tao_loc = request.GET.get('ngay_tao', '').strip()

    # 2. Lấy danh sách tài khoản kèm User, Nhân viên và Khách hàng
    tai_khoan_list = TaiKhoan.objects.select_related(
        'user', 'ho_so_nhan_vien', 'ho_so_khach_hang'
    ).all()

    if query:
        tai_khoan_list = tai_khoan_list.filter(
            Q(ma_tk__icontains=query)
            | Q(user__username__icontains=query)
            | Q(so_dien_thoai__icontains=query)
            | Q(user__email__icontains=query)
        )

    if vai_tro:
        if vai_tro in ['Quản trị viên', 'Admin']:
            tai_khoan_list = tai_khoan_list.filter(vai_tro__in=['Quản trị viên', 'Admin'])
        else:
            tai_khoan_list = tai_khoan_list.filter(vai_tro=vai_tro)

    if trang_thai == 'hoat_dong':
        tai_khoan_list = tai_khoan_list.filter(user__is_active=True)
    elif trang_thai == 'da_khoa':
        tai_khoan_list = tai_khoan_list.filter(user__is_active=False)

    today = timezone.localdate()
    dau_thang = today.replace(day=1)
    if ngay_tao_loc == 'thang_nay':
        tai_khoan_list = tai_khoan_list.filter(
            ngay_tao__date__gte=dau_thang,
            ngay_tao__date__lte=today,
        )
    elif ngay_tao_loc == '30_ngay':
        tu_ngay = today - timedelta(days=29)
        tai_khoan_list = tai_khoan_list.filter(
            ngay_tao__date__gte=tu_ngay,
            ngay_tao__date__lte=today,
        )

    tai_khoan_list = tai_khoan_list.order_by('-ngay_tao', '-ma_tk')

    # 3. Xuất file CSV (UTF-8 with BOM)
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="danh_sach_tai_khoan.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Mã tài khoản',
            'Tên đăng nhập',
            'Họ và tên',
            'Số điện thoại',
            'Email',
            'Vai trò',
            'Trạng thái',
            'Ngày tạo'
        ])

        # NẠP TÊN, GIỚI TÍNH, NGÀY SINH VÀ AVATAR CHO TỪNG DÒNG HIỂN THỊ
        for tk in page_obj.object_list:
            username = tk.user.username if tk.user else 'TK'
            tk.avatar_initials = username[:2].upper()

            nhan_vien = getattr(tk, 'ho_so_nhan_vien', None)
            khach_hang = getattr(tk, 'ho_so_khach_hang', None)
            if nhan_vien and nhan_vien.ho_ten:
                tk.display_ho_ten = nhan_vien.ho_ten
                tk.display_gioi_tinh = nhan_vien.gioi_tinh or 'Nam'
                tk.display_ngay_sinh = nhan_vien.ngay_sinh.strftime('%Y-%m-%d') if nhan_vien.ngay_sinh else ''
            elif khach_hang and khach_hang.ho_ten:
                tk.display_ho_ten = khach_hang.ho_ten
                tk.display_gioi_tinh = khach_hang.gioi_tinh or 'Nam'
                tk.display_ngay_sinh = khach_hang.ngay_sinh.strftime('%Y-%m-%d') if khach_hang.ngay_sinh else ''
            else:
                tk.display_ho_ten = tk.user.get_full_name() or tk.user.username
                tk.display_gioi_tinh = 'Nam'
                tk.display_ngay_sinh = ''
        return response

    # 4. Thống kê 4 ô
    tong_tai_khoan = TaiKhoan.objects.count()
    tong_khach_hang = KhachHang.objects.count()
    tong_nhan_su = max(0, TaiKhoan.objects.filter(
        vai_tro__in=['Nhân viên', 'Nhân viên CSKH', 'Chuyên viên', 'Quản trị viên', 'Admin']).count())
    tai_khoan_hoat_dong = TaiKhoan.objects.filter(user__is_active=True).count()

    # 5. Phân trang
    paginator = Paginator(tai_khoan_list, 8)
    page_obj = paginator.get_page(request.GET.get('page'))

    # NẠP TÊN VÀ AVATAR CHO TỪNG DÒNG HIỂN THỊ
    for tk in page_obj.object_list:
        username = tk.user.username if tk.user else 'TK'
        tk.avatar_initials = username[:2].upper()

        nhan_vien = getattr(tk, 'ho_so_nhan_vien', None)
        khach_hang = getattr(tk, 'ho_so_khach_hang', None)
        if nhan_vien and nhan_vien.ho_ten:
            tk.display_ho_ten = nhan_vien.ho_ten
        elif khach_hang and khach_hang.ho_ten:
            tk.display_ho_ten = khach_hang.ho_ten
        else:
            tk.display_ho_ten = tk.user.get_full_name() or tk.user.username

    # 6. Giữ bộ lọc khi phân trang
    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_params.pop('export', None)
    pagination_query = query_params.urlencode()

    export_params = request.GET.copy()
    export_params.pop('page', None)
    export_params['export'] = 'csv'
    export_url = '?' + export_params.urlencode()

    # 7. Danh sách số trang
    current_page = page_obj.number
    total_pages = paginator.num_pages
    page_items = []

    if total_pages <= 5:
        for number in range(1, total_pages + 1):
            page_items.append({'number': number, 'current': number == current_page})
    else:
        page_items.append({'number': 1, 'current': current_page == 1})
        start_page = max(2, current_page - 1)
        end_page = min(total_pages - 1, current_page + 1)

        if start_page > 2:
            page_items.append({'ellipsis': True})

        for number in range(start_page, end_page + 1):
            page_items.append({'number': number, 'current': number == current_page})

        if end_page < total_pages - 1:
            page_items.append({'ellipsis': True})

        page_items.append({'number': total_pages, 'current': current_page == total_pages})

    context = {
        'tai_khoan_list': page_obj.object_list,
        'page_obj': page_obj,
        'query': query,
        'vai_tro_selected': vai_tro,
        'trang_thai_selected': trang_thai,
        'ngay_tao_selected': ngay_tao_loc,
        'tong_tai_khoan_display': _format_number_vn(tong_tai_khoan),
        'tong_khach_hang_display': _format_number_vn(tong_khach_hang),
        'tong_nhan_su_display': _format_number_vn(tong_nhan_su),
        'tai_khoan_hoat_dong_display': _format_number_vn(tai_khoan_hoat_dong),
        'pagination_query': pagination_query,
        'export_url': export_url,
        'page_items': page_items,
        'showing_start': page_obj.start_index() if paginator.count else 0,
        'showing_end': page_obj.end_index() if paginator.count else 0,
        'filtered_count_display': _format_number_vn(paginator.count),
        'add_staff_form': add_staff_form or ThemNhanVienForm(),
        'show_add_modal': show_add_modal,
    }

    return render(request, 'customer/staff_account_list.html', context)


# =========================================================================
# 2. XỬ LÝ THÊM MỚI NHÂN VIÊN (TRANG RIÊNG BIỆT - CHỈ ADMIN)
# =========================================================================
@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff_user, login_url='/home/customer/')
def staff_account_add_staff_view(request):
    if not is_admin_user(request.user):
        raise PermissionDenied("Chỉ Quản trị viên mới được phép thêm nhân viên mới.")

    if request.method == 'POST':
        form = ThemNhanVienForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            vai_tro = cleaned['vai_tro']
            ho_ten = cleaned['ho_ten']
            gioi_tinh = cleaned['gioi_tinh']
            ngay_sinh = cleaned['ngay_sinh'] or date(2000, 1, 1)

            try:
                with transaction.atomic():
                    is_admin_role = (vai_tro == 'Quản trị viên')
                    user = User(
                        username=cleaned['username'],
                        email=cleaned['email'],
                        is_active=True,
                        is_staff=True,
                        is_superuser=is_admin_role
                    )
                    user.set_password(cleaned['password'])
                    user._so_dien_thoai_dang_ky = cleaned['so_dien_thoai']
                    user.save()

                    ma_tk_str = f"TK{user.id:03d}"
                    tai_khoan, _ = TaiKhoan.objects.get_or_create(
                        user=user,
                        defaults={
                            'ma_tk': ma_tk_str,
                            'so_dien_thoai': cleaned['so_dien_thoai'],
                            'vai_tro': vai_tro
                        }
                    )
                    tai_khoan.so_dien_thoai = cleaned['so_dien_thoai']
                    tai_khoan.vai_tro = vai_tro
                    tai_khoan.save(update_fields=['so_dien_thoai', 'vai_tro'])

                    ma_nv_str = f"NV{user.id:03d}"
                    while NhanVien.objects.filter(ma_nv=ma_nv_str).exists():
                        import random
                        ma_nv_str = f"NV{user.id:03d}_{random.randint(10, 99)}"

                    NhanVien.objects.create(
                        ma_nv=ma_nv_str,
                        ma_tk=tai_khoan,
                        ho_ten=ho_ten,
                        gioi_tinh=gioi_tinh,
                        ngay_sinh=ngay_sinh,
                        vi_tri=vai_tro
                    )
                    messages.success(request, f"Đã thêm mới nhân viên '{ho_ten}' ({vai_tro}) thành công!")

                return redirect('staff_account_list')

            except Exception as e:
                form.add_error(None, f"Lỗi hệ thống khi lưu: {e}")
                return render(request, 'customer/staff_staff_add.html', {'form': form})

        else:
            # Khi form có lỗi: render lại trang thêm nhân viên kèm lỗi và giá trị đã nhập
            return render(request, 'customer/staff_staff_add.html', {'form': form})

    # GET request: Hiển thị form thêm mới nhân viên rỗng
    form = ThemNhanVienForm()
    return render(request, 'customer/staff_staff_add.html', {'form': form})# =========================================================================
# =========================================================================
# 3. XỬ LÝ CHỈNH SỬA TÀI KHOẢN VÀ PHÂN QUYỀN TỪ POPUP (CHỈ ADMIN)
# =========================================================================
@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff_user, login_url='/home/customer/')
def staff_account_edit_view(request, ma_tk):
    if not is_admin_user(request.user):
        raise PermissionDenied("Chỉ Quản trị viên mới được phép chỉnh sửa phân quyền.")

    tai_khoan = get_object_or_404(TaiKhoan.objects.select_related('user'), ma_tk=ma_tk)
    user_bi_tac_dong = tai_khoan.user
    is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest')

    if request.method == 'POST':
        form = ChinhSuaTaiKhoanForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            ho_ten_moi = cleaned['ho_ten']
            sdt_moi = cleaned['so_dien_thoai']
            email_moi = cleaned['email'].strip().lower()
            vai_tro_moi = cleaned['vai_tro']
            gioi_tinh_moi = cleaned.get('gioi_tinh') or 'Nam'
            ngay_sinh_moi = cleaned.get('ngay_sinh')

            # 1. Kiểm tra trùng số điện thoại
            if TaiKhoan.objects.filter(so_dien_thoai=sdt_moi).exclude(pk=tai_khoan.pk).exists():
                err_msg = f"Số điện thoại '{sdt_moi}' đã được sử dụng bởi tài khoản khác."
                if is_ajax:
                    return JsonResponse({'success': False, 'errors': {'so_dien_thoai': [err_msg]}}, status=400)
                messages.error(request, err_msg)
                return redirect('staff_account_list')

            # 2. Kiểm tra trùng Email
            if User.objects.filter(email__iexact=email_moi).exclude(pk=user_bi_tac_dong.pk).exists():
                err_msg = f"Email '{email_moi}' đã được sử dụng bởi tài khoản khác."
                if is_ajax:
                    return JsonResponse({'success': False, 'errors': {'email': [err_msg]}}, status=400)
                messages.error(request, err_msg)
                return redirect('staff_account_list')

            # 3. Chống hạ quyền Quản trị viên duy nhất của hệ thống
            is_currently_admin = user_bi_tac_dong.is_superuser or tai_khoan.vai_tro in ['Admin', 'Quản trị viên']
            admin_count = TaiKhoan.objects.filter(
                Q(vai_tro__in=['Admin', 'Quản trị viên']) | Q(user__is_superuser=True),
                user__is_active=True
            ).count()

            if is_currently_admin and admin_count <= 1:
                if vai_tro_moi not in ['Admin', 'Quản trị viên']:
                    err_msg = "Không thể hạ quyền Quản trị viên cuối cùng đang hoạt động của hệ thống!"
                    if is_ajax:
                        return JsonResponse({'success': False, 'errors': {'__all__': [err_msg]}}, status=400)
                    messages.error(request, err_msg)
                    return redirect('staff_account_list')

            try:
                with transaction.atomic():
                    # Cập nhật Email và Vai trò của Django User (KHÔNG thay đổi is_active)
                    user_bi_tac_dong.email = email_moi

                    if vai_tro_moi in ['Admin', 'Quản trị viên']:
                        user_bi_tac_dong.is_staff = True
                        user_bi_tac_dong.is_superuser = True
                        vai_tro_db = "Quản trị viên"
                    elif vai_tro_moi in ['Nhân viên CSKH', 'Chuyên viên']:
                        user_bi_tac_dong.is_staff = True
                        user_bi_tac_dong.is_superuser = False
                        vai_tro_db = vai_tro_moi
                    else:
                        user_bi_tac_dong.is_staff = False
                        user_bi_tac_dong.is_superuser = False
                        vai_tro_db = "Khách hàng"

                    user_bi_tac_dong.save(update_fields=['email', 'is_staff', 'is_superuser'])

                    # Cập nhật Số điện thoại và Vai trò trong TAI_KHOAN
                    tai_khoan.so_dien_thoai = sdt_moi
                    tai_khoan.vai_tro = vai_tro_db
                    tai_khoan.save(update_fields=['so_dien_thoai', 'vai_tro'])

                    # Cập nhật Họ và tên, Giới tính, Ngày sinh vào hồ sơ tương ứng
                    if vai_tro_db in ['Quản trị viên', 'Nhân viên CSKH', 'Chuyên viên']:
                        nhan_vien = getattr(tai_khoan, 'ho_so_nhan_vien', None)
                        if not nhan_vien:
                            nhan_vien = NhanVien.objects.filter(ma_tk=tai_khoan).first()

                        if nhan_vien:
                            nhan_vien.ho_ten = ho_ten_moi
                            nhan_vien.vi_tri = vai_tro_moi
                            nhan_vien.gioi_tinh = gioi_tinh_moi
                            if ngay_sinh_moi:
                                nhan_vien.ngay_sinh = ngay_sinh_moi
                            nhan_vien.save(update_fields=['ho_ten', 'vi_tri', 'gioi_tinh', 'ngay_sinh'])
                        else:
                            NhanVien.objects.create(
                                ma_nv=f"NV{user_bi_tac_dong.id:03d}",
                                ma_tk=tai_khoan,
                                ho_ten=ho_ten_moi,
                                gioi_tinh=gioi_tinh_moi,
                                ngay_sinh=ngay_sinh_moi or date(2000, 1, 1),
                                vi_tri=vai_tro_moi
                            )
                    else:
                        khach_hang = getattr(tai_khoan, 'ho_so_khach_hang', None)
                        if not khach_hang:
                            khach_hang = KhachHang.objects.filter(ma_tk=tai_khoan).first()

                        if khach_hang:
                            khach_hang.ho_ten = ho_ten_moi
                            khach_hang.gioi_tinh = gioi_tinh_moi
                            if ngay_sinh_moi:
                                khach_hang.ngay_sinh = ngay_sinh_moi
                            khach_hang.save(update_fields=['ho_ten', 'gioi_tinh', 'ngay_sinh'])
                        else:
                            hang_mac_dinh = HangThanhVien.objects.order_by('diem_toi_thieu').first()
                            KhachHang.objects.create(
                                ma_kh=f"KH{user_bi_tac_dong.id:03d}",
                                ma_tk=tai_khoan,
                                ho_ten=ho_ten_moi,
                                gioi_tinh=gioi_tinh_moi,
                                ngay_sinh=ngay_sinh_moi,
                                ma_tv=hang_mac_dinh,
                                diem_tich_luy_kh=0
                            )

                messages.success(request, f"Cập nhật tài khoản '{user_bi_tac_dong.username}' thành công!")
                if is_ajax:
                    return JsonResponse({'success': True})
            except Exception as e:
                err_msg = f"Lỗi khi cập nhật tài khoản: {e}"
                if is_ajax:
                    return JsonResponse({'success': False, 'errors': {'__all__': [err_msg]}}, status=400)
                messages.error(request, err_msg)
        else:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
            first_error = next(iter(form.errors.values()))[0]
            messages.error(request, f"Không thể lưu thay đổi: {first_error}")

    return redirect('staff_account_list')
# =========================================================================
# 4. KHÓA / MỞ KHÓA NHANH TÀI KHOẢN (CHỈ ADMIN)
# =========================================================================
@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff_user, login_url='/home/customer/')
def staff_toggle_account_status_view(request, ma_tk):
    if not is_admin_user(request.user):
        raise PermissionDenied("Chỉ Quản trị viên mới được phép khóa hoặc mở khóa tài khoản.")

    tai_khoan = get_object_or_404(TaiKhoan.objects.select_related('user'), ma_tk=ma_tk)
    user_bi_tac_dong = tai_khoan.user

    if user_bi_tac_dong and request.method == 'POST':
        ly_do_chon = request.POST.get('ly_do', '').strip()
        ly_do_khac = request.POST.get('ly_do_khac', '').strip()
        ly_do_chi_tiet = ly_do_khac if ly_do_chon == 'Lý do khác' else ly_do_chon

        trang_thai_moi = not user_bi_tac_dong.is_active
        user_bi_tac_dong.is_active = trang_thai_moi
        user_bi_tac_dong.save(update_fields=['is_active'])

        hanh_dong_str = "Mở khóa" if trang_thai_moi else "Khóa"
        tai_khoan_thuc_hien = getattr(request.user, 'thong_tin_tai_khoan', None)

        try:
            count_ls = LichSuTaiKhoan.objects.count() + 1
            LichSuTaiKhoan.objects.create(
                ma_ls=f"LS{count_ls:03d}",
                ma_tk=tai_khoan,
                ma_tk_thuc_hien=tai_khoan_thuc_hien if tai_khoan_thuc_hien else tai_khoan,
                hanh_dong=hanh_dong_str,
                ly_do=ly_do_chi_tiet or "Thực hiện qua quản trị người dùng."
            )
        except Exception as e:
            print(f"Không ghi được lịch sử: {e}")

    return redirect('staff_account_list')

# =========================================================================
# CẬP NHẬT DỊCH VỤ ĐÃ SỬ DỤNG CHO KHÁCH HÀNG
# =========================================================================
@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff_user, login_url='/home/customer/')
def staff_customer_record_service_view(request, ma_kh):
    """
    Ghi nhận dịch vụ đã sử dụng cho khách hàng:
    - Hiển thị thông tin dịch vụ và khách hàng theo layout 2 cột.
    - Chỉ cho phép chọn nhân viên có vai trò Chuyên viên và tài khoản đang hoạt động.
    - Tự động tính giá và giảm giá theo hạng thành viên.
    - Lưu vào bảng DichVuDaSuDung qua transaction.atomic.
    - Tự động cộng điểm tích lũy và nâng hạng thành viên nếu đủ điều kiện.
    """
    # 2. Lấy hồ sơ khách hàng
    khach_hang = get_object_or_404(
        KhachHang.objects.select_related('ma_tk', 'ma_tk__user', 'ma_tv'),
        ma_kh=ma_kh
    )

    tai_khoan = khach_hang.ma_tk
    user = tai_khoan.user if tai_khoan else None

    # 3. Lấy danh sách dịch vụ và chỉ lọc chuyên viên đang hoạt động
    dich_vu_list = DichVu.objects.all().order_by('ten_dich_vu')
    nhan_vien_list = (
        NhanVien.objects.select_related('ma_tk__user')
        .filter(ma_tk__user__is_active=True)
        .filter(Q(vi_tri='Chuyên viên') | Q(ma_tk__vai_tro='Chuyên viên'))
        .exclude(vi_tri__in=['Quản trị viên', 'Nhân viên CSKH'])
        .exclude(ma_tk__vai_tro__in=['Quản trị viên', 'Admin', 'Nhân viên CSKH', 'Khách hàng'])
        .order_by('ho_ten')
    )

    # Hạng thành viên & tỷ lệ giảm giá hiện tại
    hang_tv = khach_hang.ma_tv
    ty_le_giam_gia = hang_tv.ty_le_giam_gia if hang_tv else Decimal('0.00')
    ten_hang = hang_tv.ten_hang if hang_tv else 'Chưa có hạng'

    # 4. Chuẩn bị dữ liệu danh mục dịch vụ dạng JSON để JavaScript tính giá tương tác
    services_dict = {}
    for dv in dich_vu_list:
        services_dict[str(dv.ma_dv)] = {
            'ma_dv': dv.ma_dv,
            'ten_dich_vu': dv.ten_dich_vu,
            'loai_dich_vu': dv.loai_dich_vu or 'Dịch vụ chăm sóc',
            'mo_ta': dv.mo_ta or 'Không có mô tả chi tiết.',
            'thoi_luong': dv.thoi_luong or 0,
            'gia_dich_vu': float(dv.gia_dich_vu),
            'diem_tich_luy': dv.diem_tich_luy_dich_vu or 0,
        }
    services_json = json.dumps(services_dict, ensure_ascii=False)

    errors = []

    # 5. Xử lý khi nhấn nút Lưu thông tin sử dụng (POST)
    if request.method == 'POST':
        ma_dv = request.POST.get('ma_dv', '').strip()
        ma_nv = request.POST.get('ma_nv', '').strip()
        ngay_su_dung_str = request.POST.get('ngay_su_dung', '').strip()
        chi_nhanh = request.POST.get('chi_nhanh', 'Charm Spa Grand – Đà Nẵng').strip()
        ghi_chu = request.POST.get('ghi_chu', '').strip()

        if not ma_dv:
            errors.append('Vui lòng chọn dịch vụ đã sử dụng.')
        if not ma_nv:
            errors.append('Vui lòng chọn nhân viên thực hiện.')

        dich_vu = DichVu.objects.filter(ma_dv=ma_dv).first()

        # Kiểm tra nhân viên phải có vai trò Chuyên viên và tài khoản đang hoạt động
        nhan_vien = (
            NhanVien.objects.select_related('ma_tk__user')
            .filter(ma_nv=ma_nv, ma_tk__user__is_active=True)
            .filter(Q(vi_tri='Chuyên viên') | Q(ma_tk__vai_tro='Chuyên viên'))
            .exclude(vi_tri__in=['Quản trị viên', 'Nhân viên CSKH'])
            .exclude(ma_tk__vai_tro__in=['Quản trị viên', 'Admin', 'Nhân viên CSKH', 'Khách hàng'])
            .first()
        )

        if not dich_vu:
            errors.append('Dịch vụ đã chọn không tồn tại trên hệ thống.')
        if not nhan_vien:
            errors.append('Nhân viên thực hiện không hợp lệ hoặc không phải là Chuyên viên đang hoạt động.')

        ngay_su_dung_val = parse_date(ngay_su_dung_str) if ngay_su_dung_str else None

        if not errors:
            try:
                with transaction.atomic():
                    # 5.1. Sinh mã sử dụng duy nhất (độ dài tối đa 10 ký tự theo model)
                    count_sd = DichVuDaSuDung.objects.count() + 1
                    ma_sd = f"SD{count_sd:05d}"
                    while DichVuDaSuDung.objects.filter(ma_sd=ma_sd).exists():
                        count_sd += 1
                        ma_sd = f"SD{count_sd:05d}"

                    # 5.2. Tạo bản ghi DichVuDaSuDung
                    su_dung = DichVuDaSuDung.objects.create(
                        ma_sd=ma_sd,
                        ma_kh=khach_hang,
                        ma_nv=nhan_vien,
                        ma_dv=dich_vu
                    )

                    # Cập nhật ngày sử dụng thực tế do nhân viên chọn
                    if ngay_su_dung_val:
                        ngay_gio = timezone.make_aware(
                            datetime.datetime.combine(ngay_su_dung_val, datetime.time(9, 0, 0))
                        )
                        DichVuDaSuDung.objects.filter(pk=ma_sd).update(ngay_su_dung=ngay_gio)

                    # 5.3. Cộng điểm tích lũy dịch vụ
                    diem_cong = dich_vu.diem_tich_luy_dich_vu or 0
                    khach_hang.diem_tich_luy_kh = (khach_hang.diem_tich_luy_kh or 0) + diem_cong

                    # 5.4. Tự động kiểm tra và nâng hạng thành viên nếu đủ điều kiện
                    hang_moi = (
                        HangThanhVien.objects.filter(diem_toi_thieu__lte=khach_hang.diem_tich_luy_kh)
                        .order_by('-diem_toi_thieu')
                        .first()
                    )

                    thong_bao_len_hang = ""
                    if hang_moi and (not khach_hang.ma_tv or khach_hang.ma_tv.pk != hang_moi.pk):
                        khach_hang.ma_tv = hang_moi
                        thong_bao_len_hang = f" Khách hàng đã được tự động thăng hạng lên: {hang_moi.ten_hang}!"

                    khach_hang.save(update_fields=['diem_tich_luy_kh', 'ma_tv'])

                messages.success(
                    request,
                    f"Ghi nhận dịch vụ '{dich_vu.ten_dich_vu}' thành công! "
                    f"(+{diem_cong} điểm tích lũy).{thong_bao_len_hang}"
                )
                return redirect('staff_customer_detail', ma_kh=khach_hang.ma_kh)

            except Exception as e:
                errors.append(f"Không thể lưu thông tin dịch vụ: {e}")

    # Chữ cái đại diện avatar khách hàng
    initials = _get_customer_initials(khach_hang.ho_ten)

    context = {
        'khach_hang': khach_hang,
        'tai_khoan': tai_khoan,
        'user': user,
        'initials': initials,
        'dich_vu_list': dich_vu_list,
        'nhan_vien_list': nhan_vien_list,
        'hang_tv': hang_tv,
        'ten_hang': ten_hang,
        'ty_le_giam_gia': ty_le_giam_gia,
        'services_json': services_json,
        'today': timezone.now().date(),
        'errors': errors,
    }

    return render(request, 'customer/staff_customer_record_service.html', context)