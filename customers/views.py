from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from customers.models import KhachHang

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from customers.models import KhachHang
from django.utils.dateparse import parse_date
from django.db import transaction

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from customers.models import KhachHang
from django.utils.dateparse import parse_date
from django.db import transaction

# =========================================================================
# XEM VÀ CHỈNH SỬA HỒ SƠ CÁ NHÂN (DÀNH CHO KHÁCH HÀNG)
# =========================================================================
@login_required(login_url='/accounts/dang_nhap/')
def customer_profile_view(request):
    """
    Xem và chỉnh sửa hồ sơ khách hàng:
    - Nếu là Staff/Admin: điều hướng về /home/staff/.
    - Cho phép cập nhật Email (User), Họ tên, Ngày sinh, Giới tính (KhachHang), Số điện thoại (TaiKhoan).
    - Sử dụng chính xác related_name="thong_tin_tai_khoan" để lưu số điện thoại.
    """
    if request.user.is_staff or request.user.is_superuser:
        return redirect('/home/staff/')

    # 1. Truy xuất thông tin TaiKhoan thông qua related_name chuẩn xác
    tai_khoan = getattr(request.user, 'thong_tin_tai_khoan', None)

    # 2. Truy xuất hồ sơ KhachHang liên kết
    khach_hang = None
    if tai_khoan:
        khach_hang = getattr(tai_khoan, 'ho_so_khach_hang', None)
    if not khach_hang:
        khach_hang = KhachHang.objects.filter(ma_tk__user=request.user).first()

    # 3. Lịch sử dịch vụ (tạm thời để an toàn, sẽ hoàn thiện ở Giai đoạn 2)
    lich_su_dich_vu = []
    if khach_hang:
        try:
            lich_su_dich_vu = khach_hang.dichvudasudung_set.select_related('ma_dv', 'ma_nv').all()[:4]
        except Exception:
            lich_su_dich_vu = []

    # 4. Xử lý khi khách hàng gửi form cập nhật
    errors = []
    if request.method == 'POST':
        ho_ten_moi = request.POST.get('ho_ten', '').strip()
        sdt_moi = request.POST.get('so_dien_thoai', '').strip()
        email_moi = request.POST.get('email', '').strip()
        ngay_sinh_moi_text = request.POST.get('ngay_sinh', '').strip()
        gioi_tinh_moi = request.POST.get('gioi_tinh', '').strip()

        ngay_sinh_moi = parse_date(ngay_sinh_moi_text) if ngay_sinh_moi_text else None

        # Kiểm tra trùng số điện thoại với tài khoản khác
        if sdt_moi and tai_khoan:
            trung_sdt = TaiKhoan.objects.filter(so_dien_thoai=sdt_moi).exclude(pk=tai_khoan.pk).exists()
            if trung_sdt:
                errors.append("Số điện thoại này đã được sử dụng bởi một tài khoản khác.")

        # Kiểm tra trùng email với tài khoản khác
        if email_moi:
            trung_email = User.objects.filter(email__iexact=email_moi).exclude(pk=request.user.pk).exists()
            if trung_email:
                errors.append("Email này đã được sử dụng bởi một tài khoản khác.")

        if not errors:
            try:
                with transaction.atomic():
                    # Cập nhật Email cho Django User
                    if email_moi != request.user.email:
                        request.user.email = email_moi
                        request.user.save(update_fields=['email'])

                    # Cập nhật thông tin KhachHang
                    if khach_hang:
                        if ho_ten_moi:
                            khach_hang.ho_ten = ho_ten_moi
                        khach_hang.ngay_sinh = ngay_sinh_moi
                        if gioi_tinh_moi in ('Nam', 'Nữ', 'Khác'):
                            khach_hang.gioi_tinh = gioi_tinh_moi
                        khach_hang.save()

                    # Cập nhật số điện thoại cho TaiKhoan (Sử dụng đối tượng tai_khoan đã sửa related_name)
                    if tai_khoan and sdt_moi:
                        tai_khoan.so_dien_thoai = sdt_moi
                        tai_khoan.save(update_fields=['so_dien_thoai'])

                return redirect('customer_profile')

            except Exception as e:
                print(f"Lỗi khi cập nhật profile: {e}")
                errors.append(f"Không thể lưu thay đổi: {e}")

    is_editing = request.GET.get('edit') == 'true'

    # Tạo đối tượng tạm nếu tài khoản chưa có bản ghi KhachHang trong database
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

    context = {
        'khach_hang': khach_hang,
        'tai_khoan': tai_khoan,
        'lich_su_dich_vu': lich_su_dich_vu,
        'is_editing': is_editing,
        'errors': errors,
    }

    return render(request, 'customer/customer_profile.html', context)
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required


@login_required(login_url='/accounts/dang_nhap/')
def customer_lock_account_view(request):
    if request.method == 'POST':
        ly_do = request.POST.get('ly_do')
        ly_do_khac = request.POST.get('ly_do_khac', '')

        # Ghi nhận lý do khóa nếu cần lưu vào log/database (tuỳ chọn)
        # Ví dụ: thiet_lap_trang_thai_khoa(...)

        # Khóa tài khoản Django User (is_active = False)
        user = request.user
        user.is_active = False
        user.save()

        # Nếu model TaiKhoan có trường trạng thái, cập nhật luôn ở đây
        tai_khoan = getattr(user, 'tai_khoan', None)
        if tai_khoan:
            tai_khoan.trang_thai = "Đã khóa"
            tai_khoan.save()

        # Đăng xuất người dùng ngay lập tức
        logout(request)

        # Chuyển hướng về trang đăng nhập hoặc trang chủ kèm thông báo
        return redirect('/accounts/dang_nhap/')

    return redirect('customer_profile')


from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from accounts.models import LichSuTaiKhoan
from customers.models import KhachHang

from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from accounts.models import LichSuTaiKhoan


# =========================================================================
# KHÁCH HÀNG TỰ KHÓA TÀI KHOẢN
# =========================================================================
@login_required(login_url='/accounts/dang_nhap/')
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
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Q
from .models import KhachHang

# Thêm các import này ở đầu customers/views.py nếu chưa có.
import csv
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.text import slugify
from django.utils import timezone
from django.core.paginator import Paginator

from customers.models import KhachHang, HangThanhVien


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

import csv

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.core.paginator import Paginator

from customers.models import KhachHang, HangThanhVien
@login_required(login_url='/accounts/dang_nhap/')
def staff_customer_list_view(request):
    # 1. Phân quyền
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('/home/customer/')

    today = timezone.localdate()

    query = request.GET.get('q', '').strip()
    hang = request.GET.get('hang', '').strip()
    trang_thai = request.GET.get('trang_thai', '').strip()
    ngay_tham_gia = request.GET.get('ngay_tham_gia', '').strip()

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

    # 5. Lọc trạng thái tài khoản
    if trang_thai == 'hoat_dong':
        khach_hang_list = khach_hang_list.filter(
            ma_tk__user__is_active=True
        )
    elif trang_thai == 'da_khoa':
        khach_hang_list = khach_hang_list.filter(
            ma_tk__user__is_active=False
        )
    elif trang_thai == 'chua_tai_khoan':
        khach_hang_list = khach_hang_list.filter(
            ma_tk__isnull=True
        )

    # 6. Lọc ngày tham gia từ TaiKhoan.ngay_tao
    dau_thang = today.replace(day=1)

    if ngay_tham_gia == 'thang_nay':
        khach_hang_list = khach_hang_list.filter(
            ma_tk__ngay_tao__date__gte=dau_thang,
            ma_tk__ngay_tao__date__lte=today,
        )
    elif ngay_tham_gia == '30_ngay':
        tu_ngay = today - timezone.timedelta(days=29)

        khach_hang_list = khach_hang_list.filter(
            ma_tk__ngay_tao__date__gte=tu_ngay,
            ma_tk__ngay_tao__date__lte=today,
        )

    khach_hang_list = khach_hang_list.order_by(
        '-ma_tk__ngay_tao',
        '-ma_kh',
    )

    # 7. Thống kê tổng quan
    tong_khach_hang = KhachHang.objects.count()

    khach_vip = KhachHang.objects.filter(
        Q(ma_tv__ten_hang__icontains='Vàng')
        | Q(ma_tv__ten_hang__icontains='Kim cương')
        | Q(ma_tv__ten_hang__icontains='VIP')
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

    # 10. Chuẩn bị dữ liệu hiển thị
    def dinh_dang_so(value):
        return f'{value:,}'.replace(',', '.')

    for kh in page_obj.object_list:
        ten = (kh.ho_ten or '').strip().split()

        kh.avatar_initials = (
            (ten[-2][0] + ten[-1][0]).upper()
            if len(ten) >= 2
            else (ten[0][:2].upper() if ten else 'KH')
        )

        kh.tier_slug = (
            slugify(kh.ma_tv.ten_hang)
            if kh.ma_tv else 'moi'
        )

        kh.points_display = dinh_dang_so(
            kh.diem_tich_luy_kh or 0
        )

    # 11. Giữ bộ lọc khi chuyển trang
    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_params.pop('export', None)
    pagination_query = query_params.urlencode()

    export_params = request.GET.copy()
    export_params.pop('page', None)
    export_params['export'] = 'csv'
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

        'tong_khach_hang_display': dinh_dang_so(
            tong_khach_hang
        ),
        'khach_vip_display': dinh_dang_so(khach_vip),
        'khach_moi_thang_nay_display': dinh_dang_so(
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
        'filtered_count_display': dinh_dang_so(
            paginator.count
        ),
    }

    return render(
        request,
        'customer/staff_customer_list.html',
        context,
    )


# Add these imports to customers/views.py if they are not already present:
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from customers.models import KhachHang



from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.db import transaction

from customers.models import KhachHang
from accounts.models import TaiKhoan


@login_required(login_url='/accounts/dang_nhap/')
def staff_customer_detail_view(request, ma_kh):
    # 1. Kiểm tra quyền nhân viên
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('/home/customer/')

    # 2. Lấy hồ sơ khách hàng cùng tài khoản liên kết
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

    # 3. Xác định trạng thái tài khoản
    if not tai_khoan:
        trang_thai_tai_khoan = 'Chưa có tài khoản'
        trang_thai_class = 'neutral'
    elif user and user.is_active:
        trang_thai_tai_khoan = 'Đang hoạt động'
        trang_thai_class = 'success'
    else:
        trang_thai_tai_khoan = 'Đã khóa'
        trang_thai_class = 'danger'

    # 4. Xử lý chỉnh sửa hồ sơ
    is_editing = (
        request.GET.get('edit') == '1'
        or request.GET.get('edit') == 'true'
        or request.method == 'POST'
    )
    errors = []

    if request.method == 'POST':
        ho_ten = request.POST.get('ho_ten', '').strip()
        so_dien_thoai = request.POST.get(
            'so_dien_thoai', ''
        ).strip()
        email = request.POST.get('email', '').strip()
        ngay_sinh_text = request.POST.get('ngay_sinh', '').strip()
        gioi_tinh = request.POST.get('gioi_tinh', '').strip()

        ngay_sinh = parse_date(ngay_sinh_text) if ngay_sinh_text else None

        # Kiểm tra dữ liệu
        if not ho_ten:
            errors.append('Họ và tên không được để trống.')

        if not so_dien_thoai:
            errors.append('Số điện thoại không được để trống.')

        if ngay_sinh_text and ngay_sinh is None:
            errors.append('Ngày sinh không hợp lệ.')

        if gioi_tinh not in ('Nam', 'Nữ', 'Khác', ''):
            errors.append('Giới tính không hợp lệ.')

        # Kiểm tra số điện thoại đã được tài khoản khác sử dụng chưa
        if so_dien_thoai:
            tk_trung = TaiKhoan.objects.filter(
                so_dien_thoai=so_dien_thoai
            )

            if tai_khoan:
                tk_trung = tk_trung.exclude(pk=tai_khoan.pk)

            if tk_trung.exists():
                errors.append(
                    'Số điện thoại đã được sử dụng bởi tài khoản khác.'
                )

        # Chỉ lưu khi dữ liệu hợp lệ
        if not errors:
            try:
                with transaction.atomic():
                    khach_hang.ho_ten = ho_ten
                    khach_hang.ngay_sinh = ngay_sinh

                    if gioi_tinh:
                        khach_hang.gioi_tinh = gioi_tinh

                    khach_hang.save()

                    if tai_khoan:
                        tai_khoan.so_dien_thoai = so_dien_thoai
                        tai_khoan.save(update_fields=['so_dien_thoai'])

                        if user:
                            user.email = email
                            user.save(update_fields=['email'])

                messages.success(
                    request,
                    'Cập nhật hồ sơ khách hàng thành công.'
                )
                return redirect(
                    'staff_customer_detail',
                    ma_kh=khach_hang.ma_kh,
                )

            except Exception:
                errors.append(
                    'Không thể lưu thông tin. '
                    'Vui lòng kiểm tra dữ liệu và thử lại.'
                )


    # 5. Lấy lịch sử sử dụng dịch vụ trực tiếp từ bảng DichVuDaSuDung
    from services.models import DichVuDaSuDung

    danh_sach_su_dung = DichVuDaSuDung.objects.filter(
        ma_kh=khach_hang
    ).select_related('ma_dv', 'ma_nv').order_by('-ngay_su_dung')

    lich_su_dich_vu = []
    ty_le_giam_ap_dung = khach_hang.ma_tv.ty_le_giam_gia if khach_hang.ma_tv else Decimal('0.00')

    for sd in danh_sach_su_dung:
        gia_goc = sd.ma_dv.gia_dich_vu if sd.ma_dv else 0
        thanh_tien = float(gia_goc) * (1 - float(ty_le_giam_ap_dung) / 100) if gia_goc else None

        lich_su_dich_vu.append({
            'ngay': sd.ngay_su_dung,
            'dich_vu': sd.ma_dv.ten_dich_vu if sd.ma_dv else 'Dịch vụ đã sử dụng',
            'nhan_vien': sd.ma_nv.ho_ten if sd.ma_nv else '—',
            'gia_tri': thanh_tien,
            'diem': sd.ma_dv.diem_tich_luy_dich_vu if sd.ma_dv else 0,
            'trang_thai': 'Đã hoàn thành',
        })

    so_luot_su_dung = len(lich_su_dich_vu)

    # 6. Chuẩn bị dữ liệu hiển thị
    ten_parts = (khach_hang.ho_ten or '').strip().split()
    initials = (
        ''.join(part[0] for part in ten_parts[-2:]).upper()
        if ten_parts else 'KH'
    )

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
        'errors': errors,
        'form_data': request.POST if request.method == 'POST' else None,
    }

    return render(
        request,
        'customer/staff_customer_detail.html',
        context,
    )

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import KhachHang, HangThanhVien
from accounts.models import TaiKhoan # Điều chỉnh import tùy theo cấu trúc app accounts của bạn

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect
from django.utils.dateparse import parse_date

from customers.models import KhachHang, HangThanhVien
from accounts.models import TaiKhoan

User = get_user_model()


@login_required(login_url='/accounts/dang_nhap/')
def staff_customer_add_view(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('/home/customer/')

    if request.method != 'POST':
        return redirect('staff_customer_list')

    ho_ten = request.POST.get('ho_ten', '').strip()
    so_dien_thoai = request.POST.get('so_dien_thoai', '').strip()
    email = request.POST.get('email', '').strip()
    ngay_sinh_text = request.POST.get('ngay_sinh', '').strip()
    gioi_tinh = request.POST.get('gioi_tinh', 'Nam')

    ngay_sinh = parse_date(ngay_sinh_text) if ngay_sinh_text else None

    if not ho_ten or not so_dien_thoai:
        messages.error(request, 'Vui lòng nhập họ tên và số điện thoại.')
        return redirect('staff_customer_list')

    if ngay_sinh_text and ngay_sinh is None:
        messages.error(request, 'Ngày sinh không hợp lệ.')
        return redirect('staff_customer_list')

    if TaiKhoan.objects.filter(so_dien_thoai=so_dien_thoai).exists():
        messages.error(request, 'Số điện thoại đã được sử dụng.')
        return redirect('staff_customer_list')

    try:
        with transaction.atomic():
            # 1. Tạo User của Django
            username_moi = f'kh_{so_dien_thoai}'

            if User.objects.filter(username=username_moi).exists():
                messages.error(
                    request,
                    'Tên đăng nhập đã tồn tại. Vui lòng kiểm tra lại số điện thoại.'
                )
                return redirect('staff_customer_list')

            user_moi = User.objects.create_user(
                username=username_moi,
                email=email,
                password='Password123@'
            )

            # 2. Tạo hồ sơ TaiKhoan theo model của dự án
            tai_khoan_moi = TaiKhoan.objects.create(
                ma_tk=f'TK{user_moi.pk}',
                user=user_moi,
                so_dien_thoai=so_dien_thoai,
                vai_tro='Khách hàng'
            )

            # 3. Sinh mã khách hàng mới
            # Dựa vào số thứ tự lớn nhất của các mã dạng KH-00001
            ma_kh_moi = None
            for kh_cu in KhachHang.objects.filter(
                ma_kh__startswith='KH-'
            ).only('ma_kh'):
                try:
                    so_thu_tu = int(kh_cu.ma_kh.split('-')[-1])
                    if ma_kh_moi is None or so_thu_tu > ma_kh_moi:
                        ma_kh_moi = so_thu_tu
                except (ValueError, IndexError):
                    continue

            ma_kh_moi = f'KH-{(ma_kh_moi or 0) + 1:05d}'

            # 4. Lấy hạng thành viên mặc định
            hang_mac_dinh = HangThanhVien.objects.order_by(
                'diem_toi_thieu'
            ).first()

            # 5. Tạo hồ sơ khách hàng
            KhachHang.objects.create(
                ma_kh=ma_kh_moi,
                ma_tk=tai_khoan_moi,
                ma_tv=hang_mac_dinh,
                ho_ten=ho_ten,
                ngay_sinh=ngay_sinh,
                gioi_tinh=gioi_tinh,
                diem_tich_luy_kh=0
            )

        messages.success(
            request,
            f'Đã thêm khách hàng {ho_ten} thành công.'
        )


    except Exception as e:

        import traceback

        traceback.print_exc()

        messages.error(request, f"Lỗi khi thêm khách hàng: {e}")

    return redirect('staff_customer_list')


# =========================================================================
# 1. QUẢN LÝ DANH SÁCH TÀI KHOẢN TOÀN HỆ THỐNG
# =========================================================================
@login_required(login_url='/accounts/dang_nhap/')
def staff_account_list_view(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('/home/customer/')

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
        tu_ngay = today - timezone.timedelta(days=29)
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

        for tk in tai_khoan_list:
            trang_thai_text = 'Đang hoạt động' if tk.user.is_active else 'Đã khóa'
            ngay_tao_text = timezone.localtime(tk.ngay_tao).strftime('%d/%m/%Y %H:%M') if tk.ngay_tao else ''

            nv = getattr(tk, 'ho_so_nhan_vien', None)
            kh = getattr(tk, 'ho_so_khach_hang', None)
            ho_ten_xuat = nv.ho_ten if (nv and nv.ho_ten) else (kh.ho_ten if (kh and kh.ho_ten) else tk.user.username)

            writer.writerow([
                tk.ma_tk,
                tk.user.username,
                ho_ten_xuat,
                tk.so_dien_thoai,
                tk.user.email,
                tk.vai_tro,
                trang_thai_text,
                ngay_tao_text,
            ])
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
    }

    return render(request, 'customer/staff_account_list.html', context)


# =========================================================================
# 2. XỬ LÝ THÊM MỚI NHÂN VIÊN TỪ POPUP
# =========================================================================
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.models import User
from accounts.models import TaiKhoan, NhanVien, LichSuTaiKhoan
from customers.models import KhachHang, HangThanhVien
from accounts.forms import ThemNhanVienForm, ChinhSuaTaiKhoanForm
from datetime import date


@login_required(login_url='/accounts/dang_nhap/')
def staff_account_add_staff_view(request):
    # Kiểm tra quyền: Là superuser HOẶC tài khoản có vai trò Quản trị viên / Admin
    is_admin = request.user.is_superuser or (
        hasattr(request.user, 'thong_tin_tai_khoan') and
        request.user.thong_tin_tai_khoan.vai_tro in ['Quản trị viên', 'Admin']
    )
    if not is_admin:
        messages.error(request, "Bạn không có quyền thực hiện thao tác này. Chỉ Quản trị viên mới được thêm nhân viên.")
        return redirect('staff_account_list')
    if request.method == 'POST':
        form = ThemNhanVienForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            try:
                with transaction.atomic():
                    is_active = (cleaned['trang_thai'] == 'Hoạt động')
                    is_admin = (cleaned['vai_tro'] == 'Quản trị viên')

                    user = User(
                        username=cleaned['username'],
                        email=cleaned['email'],
                        is_active=is_active,
                        is_staff=True,
                        is_superuser=is_admin
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
                            'vai_tro': cleaned['vai_tro']
                        }
                    )
                    tai_khoan.so_dien_thoai = cleaned['so_dien_thoai']
                    tai_khoan.vai_tro = cleaned['vai_tro']
                    tai_khoan.save(update_fields=['so_dien_thoai', 'vai_tro'])

                    ma_nv_str = f"NV{user.id:03d}"
                    ngay_sinh = cleaned['ngay_sinh'] or date(2000, 1, 1)

                    NhanVien.objects.create(
                        ma_nv=ma_nv_str,
                        ma_tk=tai_khoan,
                        ho_ten=cleaned['ho_ten'],
                        gioi_tinh="Khác",
                        ngay_sinh=ngay_sinh,
                        vi_tri=cleaned['vai_tro']
                    )

                messages.success(request,
                                 f"Đã thêm mới nhân viên '{cleaned['ho_ten']}' ({cleaned['vai_tro']}) thành công!")
            except Exception as e:
                messages.error(request, f"Lỗi khi thêm nhân viên: {e}")
        else:
            first_error = next(iter(form.errors.values()))[0]
            messages.error(request, f"Không thể thêm nhân viên: {first_error}")

    return redirect('staff_account_list')


# =========================================================================
# 3. XỬ LÝ CHỈNH SỬA TÀI KHOẢN VÀ PHÂN QUYỀN TỪ POPUP
# =========================================================================
@login_required(login_url='/accounts/dang_nhap/')
@login_required(login_url='/accounts/dang_nhap/')
def staff_account_edit_view(request, ma_tk):
    # Kiểm tra quyền: Là superuser HOẶC tài khoản có vai trò Quản trị viên / Admin
    is_admin = request.user.is_superuser or (
        hasattr(request.user, 'thong_tin_tai_khoan') and
        request.user.thong_tin_tai_khoan.vai_tro in ['Quản trị viên', 'Admin']
    )
    if not is_admin:
        messages.error(request, "Bạn không có quyền thực hiện thao tác này. Chỉ Quản trị viên mới được phân quyền.")
        return redirect('staff_account_list')

    tai_khoan = get_object_or_404(TaiKhoan.objects.select_related('user'), ma_tk=ma_tk)
    user_bi_tac_dong = tai_khoan.user

    if request.method == 'POST':
        form = ChinhSuaTaiKhoanForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            ho_ten_moi = cleaned['ho_ten'].strip()
            sdt_moi = cleaned['so_dien_thoai'].strip()
            email_moi = cleaned['email'].strip()
            vai_tro_moi = cleaned['vai_tro']
            trang_thai_moi = cleaned['trang_thai']
            is_active_moi = (trang_thai_moi == 'Hoạt động')

            if TaiKhoan.objects.filter(so_dien_thoai=sdt_moi).exclude(pk=tai_khoan.pk).exists():
                messages.error(request, f"Số điện thoại '{sdt_moi}' đã được sử dụng bởi tài khoản khác.")
                return redirect('staff_account_list')

            if email_moi and User.objects.filter(email__iexact=email_moi).exclude(pk=user_bi_tac_dong.pk).exists():
                messages.error(request, f"Email '{email_moi}' đã được sử dụng bởi tài khoản khác.")
                return redirect('staff_account_list')

            # Chống khóa/hạ quyền admin duy nhất
            is_currently_admin = user_bi_tac_dong.is_superuser or tai_khoan.vai_tro in ['Admin', 'Quản trị viên']
            admin_count = TaiKhoan.objects.filter(
                Q(vai_tro__in=['Admin', 'Quản trị viên']) | Q(user__is_superuser=True),
                user__is_active=True
            ).count()

            if is_currently_admin and admin_count <= 1:
                if not is_active_moi:
                    messages.error(request,
                                   "Không thể khóa tài khoản Quản trị viên cuối cùng đang hoạt động của hệ thống!")
                    return redirect('staff_account_list')
                if vai_tro_moi not in ['Admin', 'Quản trị viên']:
                    messages.error(request, "Không thể hạ quyền Quản trị viên cuối cùng của hệ thống!")
                    return redirect('staff_account_list')

            try:
                with transaction.atomic():
                    user_bi_tac_dong.email = email_moi
                    trang_thai_thay_doi = (user_bi_tac_dong.is_active != is_active_moi)
                    user_bi_tac_dong.is_active = is_active_moi

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

                    user_bi_tac_dong.save(update_fields=['email', 'is_active', 'is_staff', 'is_superuser'])

                    tai_khoan.so_dien_thoai = sdt_moi
                    tai_khoan.vai_tro = vai_tro_db
                    tai_khoan.save(update_fields=['so_dien_thoai', 'vai_tro'])

                    if vai_tro_db in ['Quản trị viên', 'Nhân viên CSKH', 'Chuyên viên', 'Nhân viên']:
                        nhan_vien = getattr(tai_khoan, 'ho_so_nhan_vien', None)
                        if not nhan_vien:
                            nhan_vien = NhanVien.objects.filter(ma_tk=tai_khoan).first()

                        if nhan_vien:
                            if ho_ten_moi:
                                nhan_vien.ho_ten = ho_ten_moi
                            nhan_vien.vi_tri = vai_tro_moi
                            nhan_vien.save(update_fields=['ho_ten', 'vi_tri'])
                        else:
                            NhanVien.objects.create(
                                ma_nv=f"NV{user_bi_tac_dong.id:03d}",
                                ma_tk=tai_khoan,
                                ho_ten=ho_ten_moi or user_bi_tac_dong.username,
                                gioi_tinh="Khác",
                                ngay_sinh=date(2000, 1, 1),
                                vi_tri=vai_tro_moi
                            )
                    else:
                        khach_hang = getattr(tai_khoan, 'ho_so_khach_hang', None)
                        if not khach_hang:
                            khach_hang = KhachHang.objects.filter(ma_tk=tai_khoan).first()

                        if khach_hang:
                            if ho_ten_moi:
                                khach_hang.ho_ten = ho_ten_moi
                            khach_hang.save(update_fields=['ho_ten'])
                        else:
                            hang_mac_dinh = HangThanhVien.objects.order_by('diem_toi_thieu').first()
                            KhachHang.objects.create(
                                ma_kh=f"KH{user_bi_tac_dong.id:03d}",
                                ma_tk=tai_khoan,
                                ho_ten=ho_ten_moi or user_bi_tac_dong.username,
                                ma_tv=hang_mac_dinh,
                                diem_tich_luy_kh=0
                            )

                    if trang_thai_thay_doi:
                        hanh_dong_str = "Mở khóa" if is_active_moi else "Khóa"
                        tai_khoan_admin = getattr(request.user, 'thong_tin_tai_khoan', None)
                        count_ls = LichSuTaiKhoan.objects.count() + 1
                        LichSuTaiKhoan.objects.create(
                            ma_ls=f"LS{count_ls:03d}",
                            ma_tk=tai_khoan,
                            ma_tk_thuc_hien=tai_khoan_admin if tai_khoan_admin else tai_khoan,
                            hanh_dong=hanh_dong_str,
                            ly_do=f"Quản trị viên cập nhật trạng thái trong popup phân quyền ({hanh_dong_str})."
                        )

                messages.success(request, f"Cập nhật tài khoản '{user_bi_tac_dong.username}' thành công!")
            except Exception as e:
                messages.error(request, f"Lỗi khi cập nhật tài khoản: {e}")
        else:
            first_error = next(iter(form.errors.values()))[0]
            messages.error(request, f"Không thể lưu thay đổi: {first_error}")

    return redirect('staff_account_list')


# =========================================================================
# 4. KHÓA / MỞ KHÓA NHANH TÀI KHOẢN
# =========================================================================
@login_required(login_url='/accounts/dang_nhap/')
def staff_toggle_account_status_view(request, ma_tk):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('/home/customer/')

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
import json
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from customers.models import KhachHang, HangThanhVien
from accounts.models import NhanVien
from services.models import DichVu, DichVuDaSuDung


@login_required(login_url='/accounts/dang_nhap/')
def staff_customer_record_service_view(request, ma_kh):
    """
    Ghi nhận dịch vụ đã sử dụng cho khách hàng:
    - Hiển thị thông tin dịch vụ và khách hàng theo layout 2 cột.
    - Tự động tính giá và giảm giá theo hạng thành viên.
    - Lưu vào bảng DichVuDaSuDung qua transaction.atomic.
    - Tự động cộng điểm tích lũy và nâng hạng thành viên nếu đủ điều kiện.
    """
    # 1. Kiểm tra quyền nhân viên hoặc quản trị viên
    vai_tro = ''
    tai_khoan_hien_tai = getattr(request.user, 'thong_tin_tai_khoan', None)
    if tai_khoan_hien_tai:
        vai_tro = tai_khoan_hien_tai.vai_tro

    if not (request.user.is_staff or request.user.is_superuser or vai_tro in ['Nhân viên', 'Quản trị viên']):
        return redirect('/home/customer/')

    # 2. Lấy hồ sơ khách hàng
    khach_hang = get_object_or_404(
        KhachHang.objects.select_related('ma_tk', 'ma_tk__user', 'ma_tv'),
        ma_kh=ma_kh
    )

    tai_khoan = khach_hang.ma_tk
    user = tai_khoan.user if tai_khoan else None

    # 3. Lấy danh sách dịch vụ và nhân viên từ CSDL
    dich_vu_list = DichVu.objects.all().order_by('ten_dich_vu')
    nhan_vien_list = NhanVien.objects.all().order_by('ho_ten')

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
        nhan_vien = NhanVien.objects.filter(ma_nv=ma_nv).first()

        if not dich_vu:
            errors.append('Dịch vụ đã chọn không tồn tại trên hệ thống.')
        if not nhan_vien:
            errors.append('Nhân viên thực hiện đã chọn không tồn tại trên hệ thống.')

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
                        import datetime
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
    ten_parts = (khach_hang.ho_ten or '').strip().split()
    initials = ''.join(part[0] for part in ten_parts[-2:]).upper() if ten_parts else 'KH'

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