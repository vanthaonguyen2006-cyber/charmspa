import calendar
from functools import wraps
import json
import random
import traceback
import uuid
from datetime import date, datetime, timedelta
from customers.models import KhachHang
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
import re
from django.urls import reverse
from django.utils import timezone
from services.models import DichVu
from .forms import KhoaNgayForm
from .models import LichHen, NgayHoatDong, PhanCongLichHen
from accounts.models import (
    NhanVien, TaiKhoan, ROLE_STAFF,
    get_user_role, is_manager_role, is_staff_portal_user, is_customer_role,
)


# Decorator kiểm tra quyền theo vai trò nghiệp vụ (chỉ quản lý / chỉ tài khoản nội bộ staff portal).
manager_only = user_passes_test(is_manager_role, login_url='/accounts/dang_nhap/')
staff_portal_only = user_passes_test(is_staff_portal_user, login_url='/accounts/dang_nhap/')


# Lấy tên, chữ viết tắt, chức vụ và trạng thái quản lý để truyền ra các template.
def get_staff_context(request):
    """Lấy thông tin hiển thị theo vai trò nghiệp vụ, không dùng is_staff/is_superuser của Django Admin."""
    name = request.user.username if request.user.is_authenticated else 'Tài khoản'
    role = get_user_role(request.user)
    position = role or 'Tài khoản kỹ thuật'
    # Nếu là Khách hàng thì ưu tiên lấy họ tên đầy đủ từ bảng KhachHang.
    if role == 'Khách hàng':
        kh = KhachHang.objects.filter(ma_tk__user=request.user).first()
        if kh and kh.ho_ten:
            name = kh.ho_ten
    initials = name[:2].upper() if name else '?'
    return {
        'staff_name': name,
        'staff_initials': initials,
        'staff_position': position,
        'is_manager': is_manager_role(request.user),
    }


# UI: customer_create.html — Khách tạo lịch hẹn mới (bản gốc; cuối file có hàm bọc thêm luồng ưu đãi).
@login_required(login_url='/accounts/dang_nhap/')
def booking_customer_create(request):
    """Chỉ tài khoản khách hàng đã đăng nhập mới được đặt lịch từ trang khách."""
    # Chặn tài khoản nội bộ (staff/manager) dùng trang đặt lịch dành riêng cho khách.
    if not is_customer_role(request.user):
        return HttpResponseForbidden("Chỉ tài khoản Khách hàng mới được đặt lịch tại trang này.")

    dich_vu_list = DichVu.objects.all()

    # Lấy danh sách ngày bị khóa để gửi ra JS chặn chọn lịch và kiểm tra lại khi POST.
    locked_dates = list(
        NgayHoatDong.objects.filter(trang_thai='Đã khóa')
        .values_list('ngay', flat=True)
    )
    locked_dates_str = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in locked_dates]

    if request.method == 'POST':
        ma_dv = request.POST.get('ma_dv')
        ngay_hen = request.POST.get('ngay_hen')
        time_slot = request.POST.get('time_slot')
        ho_ten = request.POST.get('ho_ten', request.user.username)
        so_luong = request.POST.get('so_luong', 1)
        ghi_chu = request.POST.get('ghi_chu', '')

        try:
            dich_vu = get_object_or_404(DichVu, pk=ma_dv)

            # Chuẩn hóa ngày hẹn (hỗ trợ cả dd/mm/yyyy và yyyy-mm-dd) về YYYY-MM-DD.
            ngay_check = datetime.today().strftime('%Y-%m-%d')
            if ngay_hen:
                if '/' in ngay_hen:
                    date_obj = datetime.strptime(ngay_hen.strip(), '%d/%m/%Y').date()
                else:
                    date_obj = datetime.strptime(ngay_hen.strip(), '%Y-%m-%d').date()
                ngay_check = date_obj.strftime('%Y-%m-%d')

            # Chặn đặt lịch vào ngày spa đang khóa.
            if ngay_check in locked_dates_str:
                messages.error(request, "Ngày bạn chọn hiện đang đóng cửa (Nghỉ lễ/Bảo trì). Vui lòng chọn ngày khác.")
                return redirect('bookings:booking_customer_create')

            so_luong_int = int(so_luong) if so_luong else 1

            # Lấy TaiKhoan và tự tạo/cập nhật hồ sơ KhachHang nếu chưa có.
            tai_khoan_Obj = TaiKhoan.objects.get(user=request.user)

            khach_hang, _ = KhachHang.objects.get_or_create(
                ma_tk=tai_khoan_Obj,
                defaults={'ho_ten': ho_ten}
            )
            if ho_ten and khach_hang.ho_ten != ho_ten:
                khach_hang.ho_ten = ho_ten
                khach_hang.save()

            # Lấy hoặc tạo bản ghi NgayHoatDong cho ngày hẹn ở trạng thái 'Mở'.
            ngay_hd, _ = NgayHoatDong.objects.get_or_create(
                ngay=ngay_check,
                defaults={'ma_nhd': f'NHD-{ngay_check}', 'trang_thai': 'Mở'}
            )

            # Sinh mã lịch hẹn LH-xxxxxx, lưu DB rồi ghi vào session cho trang success.
            ma_lh_moi = f"LH-{random.randint(100000, 999999)}"

            LichHen.objects.create(
                ma_lh=ma_lh_moi,
                ma_kh=khach_hang,
                ma_dv=dich_vu,
                ma_nhd=ngay_hd,
                ngay_hen=ngay_check,
                gio_hen=time_slot,
                so_luong_khach=so_luong_int,
                ghi_chu=ghi_chu,
                trang_thai='Đã đặt'
            )

            request.session['last_booking_code'] = ma_lh_moi
            return redirect('bookings:booking_customer_success')

        except Exception as e:
            print("LỖI KHI ĐẶT LỊCH:", e)
            traceback.print_exc()
            messages.error(request, f"Có lỗi xảy ra khi đặt lịch: {e}")

    # GET: lấy thông tin tài khoản khách hàng đang đăng nhập để tự điền sẵn vào form.
    tai_khoan = TaiKhoan.objects.filter(
        user=request.user
    ).first()

    khach_hang = None
    if tai_khoan:
        khach_hang = KhachHang.objects.filter(
            ma_tk=tai_khoan
        ).first()

    # Chuẩn bị họ tên, SĐT, email tự động điền vào form đặt lịch.
    ho_ten = (
        khach_hang.ho_ten
        if khach_hang and khach_hang.ho_ten
        else request.user.get_full_name() or request.user.username
    )

    so_dien_thoai = (
        tai_khoan.so_dien_thoai
        if tai_khoan and tai_khoan.so_dien_thoai
        else ''
    )

    email = request.user.email or ''

    context = {
        'dich_vu_list': dich_vu_list,
        'locked_dates_json': locked_dates_str,
        'khach_hang': khach_hang,
        'booking_customer_name': ho_ten,
        'booking_customer_phone': so_dien_thoai,
        'booking_customer_email': email,
        'promo_ap_dung': _promo_hop_le_cho_booking(request),  # [THEM] Dữ liệu ưu đãi cho form
    }

    return render(request, 'bookings/customer_create.html', context)


# UI: customer_list.html — Danh sách lịch hẹn (khách xem lịch của mình; staff portal xem tất cả, lọc theo tab trạng thái).
@user_passes_test(lambda u: get_user_role(u) is not None, login_url='/accounts/dang_nhap/')
def booking_customer_list(request):
    trang_thai_filter = request.GET.get('trang_thai', '')
    khach_hang = None

    # Lấy danh sách các ngày đã khóa để truyền ra template chặn lịch khi mở modal đổi lịch.
    locked_dates = list(
        NgayHoatDong.objects.filter(trang_thai='Đã khóa')
        .values_list('ngay', flat=True)
    )
    locked_dates_str = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in locked_dates]

    # Staff portal xem tất cả lịch (trừ 'Đã xóa'); khách hàng chỉ xem lịch của chính tài khoản mình.
    if is_staff_portal_user(request.user):
        lich_hen_list = LichHen.objects.select_related('ma_dv', 'ma_kh').exclude(trang_thai='Đã xóa').order_by('-ngay_hen')
    else:
        try:
            tai_khoan_Obj = TaiKhoan.objects.get(user=request.user)
            khach_hang = KhachHang.objects.filter(ma_tk=tai_khoan_Obj).first()
            lich_hen_list = LichHen.objects.select_related('ma_dv', 'ma_kh').filter(ma_kh__ma_tk=tai_khoan_Obj).exclude(trang_thai='Đã xóa').order_by('-ngay_hen')
        except TaiKhoan.DoesNotExist:
            lich_hen_list = LichHen.objects.none()

    # Lọc danh sách theo tham số ?trang_thai= (active / completed / cancelled).
    if trang_thai_filter:
        if trang_thai_filter == 'active':
            lich_hen_list = lich_hen_list.filter(trang_thai__in=['Đã đặt', 'Đã xác nhận'])
        elif trang_thai_filter == 'completed':
            lich_hen_list = lich_hen_list.filter(trang_thai='Hoàn thành')
        elif trang_thai_filter == 'cancelled':
            lich_hen_list = lich_hen_list.filter(trang_thai='Đã hủy')

    dich_vu_list = DichVu.objects.all()

    return render(request, 'bookings/customer_list.html', {
        'lich_hen_list': lich_hen_list,
        'dich_vu_list': dich_vu_list,
        'current_filter': trang_thai_filter,
        'khach_hang': khach_hang,
        'locked_dates_json': locked_dates_str,
        **get_staff_context(request)
    })


# UI: customer_detail.html — Xem chi tiết 1 lịch hẹn phía khách (kèm danh sách dịch vụ & ngày khóa cho modal đổi lịch).
@user_passes_test(lambda u: get_user_role(u) is not None, login_url='/accounts/dang_nhap/')
def booking_customer_detail(request, ma_lh):
    # Banner hồ sơ trong customer_base_pro cần biến khach_hang.
    khach_hang = KhachHang.objects.select_related('ma_tk__user').filter(
        ma_tk__user=request.user
    ).first()

    lich_hen_qs = LichHen.objects.select_related('ma_dv', 'ma_kh__ma_tk__user', 'ma_nv').exclude(trang_thai='Đã xóa')
    # Khách chỉ được xem lịch hẹn của tài khoản chính mình.
    if not is_staff_portal_user(request.user):
        lich_hen_qs = lich_hen_qs.filter(ma_kh__ma_tk__user=request.user)
    lich_hen = get_object_or_404(lich_hen_qs, ma_lh=ma_lh)

    return render(request, 'bookings/customer_detail.html', {
        'lich_hen': lich_hen,
        'khach_hang': khach_hang,
        'dich_vu_list': DichVu.objects.all().order_by('pk'),
        'locked_dates_json': json.dumps([
            day.isoformat() for day in NgayHoatDong.objects.filter(
                trang_thai='Đã khóa'
            ).values_list('ngay', flat=True)
        ]),
        **get_staff_context(request)
    })


# UI: customer_success.html — Trang thông báo đặt lịch thành công (đọc mã lịch vừa tạo từ session).
@login_required(login_url='/accounts/dang_nhap/')
def booking_customer_success(request):
    last_code = request.session.get('last_booking_code')

    lich_hen = None

    # Chỉ lấy đúng lịch hẹn trùng mã session và thuộc user đang đăng nhập.
    if last_code:
        lich_hen = LichHen.objects.select_related(
            'ma_dv',
            'ma_kh',
            'ma_kh__ma_tk'
        ).filter(
            ma_lh=last_code,
            ma_kh__ma_tk__user=request.user
        ).first()

    khach_hang = KhachHang.objects.select_related(
        'ma_tk',
        'ma_tv'
    ).filter(
        ma_tk__user=request.user
    ).first()

    return render(request, 'bookings/customer_success.html', {
        'lich_hen': lich_hen,
        'khach_hang': khach_hang,
        **get_staff_context(request)
    })


# UI: modal/form hủy lịch của khách — Hủy lịch (chuyển trạng thái 'Đã hủy', bắt buộc trước 6 tiếng và có lý do).
@login_required(login_url='/accounts/dang_nhap/')
def booking_customer_cancel(request, ma_lh):
    """Đổi trạng thái lịch thành Đã hủy, giữ bản ghi trong database."""
    # Chỉ nhận POST (từ form/modal hủy lịch); truy cập GET thì quay về danh sách.
    if request.method != 'POST':
        return redirect('bookings:booking_customer_list')

    # Tìm lịch theo ma_lh và bắt buộc thuộc tài khoản khách hàng đang đăng nhập.
    lich_hen = get_object_or_404(
        LichHen, ma_lh=ma_lh, ma_kh__ma_tk__user=request.user
    )

    # Chặn hủy nếu lịch đã hủy, đã hoàn thành hoặc đã xóa.
    if lich_hen.trang_thai in ('Đã hủy', 'Hoàn thành', 'Đã xóa'):
        messages.error(request, 'Lịch hẹn này không thể hủy.')
        return redirect('bookings:booking_customer_list')

    # Ghép ngày hẹn + giờ hẹn, quy về timezone hiện tại rồi so với thời điểm hiện tại.
    ngay_gio_hen = datetime.combine(lich_hen.ngay_hen, lich_hen.gio_hen)
    if timezone.is_naive(ngay_gio_hen):
        ngay_gio_hen = timezone.make_aware(
            ngay_gio_hen, timezone.get_current_timezone()
        )

    # Nếu còn dưới 6 tiếng trước giờ hẹn thì không cho khách tự hủy.
    if ngay_gio_hen - timezone.now() < timedelta(hours=6):
        messages.error(
            request, 'Không thể hủy! Chỉ được hủy trước giờ hẹn ít nhất 6 tiếng.'
        )
        return redirect('bookings:booking_customer_list')

    # Đọc lý do hủy; nếu chọn 'Khác' thì lấy nội dung nhập ở ô ly_do_khac; trống thì báo lỗi.
    ly_do = request.POST.get('ly_do_huy', '').strip()
    if ly_do == 'Khác':
        ly_do = request.POST.get('ly_do_khac', '').strip()
    if not ly_do:
        messages.error(request, 'Vui lòng nhập lý do hủy lịch.')
        return redirect('bookings:booking_customer_list')

    # Cập nhật trạng thái + lý do hủy vào DB (giữ lại record) rồi chuyển tab cancelled.
    lich_hen.trang_thai = 'Đã hủy'
    lich_hen.ly_do_huy = ly_do
    lich_hen.save(update_fields=['trang_thai', 'ly_do_huy'])

    messages.success(request, f'Đã hủy lịch #{lich_hen.ma_lh} thành công.')
    return redirect(reverse('bookings:booking_customer_list') + '?trang_thai=cancelled')


# UI: modal/form đổi lịch ở list/detail — Đổi lịch bản gốc (check 3 tiếng, ngày/giờ mới, ngày khóa, sức chứa giường).
@user_passes_test(lambda u: get_user_role(u) is not None, login_url='/accounts/dang_nhap/')
def booking_customer_reschedule(request, ma_lh):
    # Quay về đúng giao diện danh sách của người đang thực hiện đổi lịch (staff hoặc khách).
    redirect_url = (
        'bookings:staff_booking_list'
        if is_staff_portal_user(request.user)
        else 'bookings:booking_customer_list'
    )
    if request.method == "POST":
        # Khách chỉ được đổi lịch của chính mình; staff/manager đổi được mọi lịch.
        lich_hen_qs = LichHen.objects.all()
        if not is_staff_portal_user(request.user):
            lich_hen_qs = lich_hen_qs.filter(ma_kh__ma_tk__user=request.user)
        lich_hen = get_object_or_404(lich_hen_qs, ma_lh=ma_lh)

        # Kiểm tra mốc 3 tiếng trước giờ hẹn cũ: dưới 3 * 3600 giây thì chặn đổi.
        try:
            time_part = str(lich_hen.gio_hen).split()[0]
            hour_min = time_part.split(':')
            h = int(hour_min[0])
            m = int(hour_min[1]) if len(hour_min) > 1 else 0

            if 'p.m.' in str(lich_hen.gio_hen).lower() and h < 12:
                h += 12

            appointment_dt = datetime.combine(datetime.strptime(str(lich_hen.ngay_hen), '%Y-%m-%d').date(),
                                              datetime.min.time().replace(hour=h, minute=m))
            time_difference = appointment_dt - datetime.now()

            if time_difference.total_seconds() < 3 * 3600:
                messages.error(request,
                               "Không thể đổi lịch! Chỉ được phép thay đổi lịch hẹn trước ít nhất 3 tiếng so với giờ hẹn.")
                return redirect(redirect_url)
        except Exception as e:
            print("Lỗi check thời gian đổi lịch:", e)

        ngay_hen_moi = request.POST.get('ngay_hen_moi')
        gio_hen_moi = request.POST.get('gio_hen_moi')
        ma_dv_moi = request.POST.get('ma_dv_moi')
        so_luong_moi = request.POST.get('so_luong_khach_moi')
        ghi_chu_moi = request.POST.get('ghi_chu_moi')

        # Chặn form Đổi lịch thiếu ngày/giờ hoặc chọn thời điểm trong quá khứ.
        if not (ngay_hen_moi or '').strip():
            messages.error(request, 'Vui lòng chọn ngày hẹn mới.')
            return redirect(redirect_url)
        if not (gio_hen_moi or '').strip():
            messages.error(request, 'Vui lòng chọn khung giờ hẹn mới.')
            return redirect(redirect_url)
        try:
            raw_date = ngay_hen_moi.strip()
            ngay_moi_kiem_tra = datetime.strptime(
                raw_date, '%d/%m/%Y' if '/' in raw_date else '%Y-%m-%d'
            ).date()
            gio_moi_kiem_tra = datetime.strptime(gio_hen_moi.strip(), '%H:%M').time()
        except (TypeError, ValueError):
            messages.error(request, 'Ngày hoặc giờ hẹn không hợp lệ. Vui lòng chọn lại.')
            return redirect(redirect_url)
        ngay_gio_moi = datetime.combine(ngay_moi_kiem_tra, gio_moi_kiem_tra)
        if timezone.make_aware(ngay_gio_moi, timezone.get_current_timezone()) <= timezone.now():
            messages.error(request, 'Không thể đổi lịch sang thời điểm đã qua.')
            return redirect(redirect_url)

        dich_vu_hien_tai = lich_hen.ma_dv
        if ma_dv_moi:
            dich_vu_moi = DichVu.objects.filter(pk=ma_dv_moi).first()
            if dich_vu_moi:
                dich_vu_hien_tai = dich_vu_moi

        ngay_str = lich_hen.ngay_hen
        if ngay_hen_moi:
            try:
                if '/' in ngay_hen_moi:
                    date_obj = datetime.strptime(ngay_hen_moi.strip(), '%d/%m/%Y').date()
                else:
                    date_obj = datetime.strptime(ngay_hen_moi.strip(), '%Y-%m-%d').date()
                ngay_str = date_obj.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                pass

        # Chặn đổi sang ngày đã bị khóa.
        if NgayHoatDong.objects.filter(ngay=ngay_str, trang_thai='Đã khóa').exists():
            messages.error(request, 'Ngày mới đã bị khóa. Vui lòng chọn ngày khác.')
            return redirect(redirect_url)

        gio_str = gio_hen_moi if gio_hen_moi else lich_hen.gio_hen

        try:
            so_luong_int = int(so_luong_moi) if so_luong_moi else lich_hen.so_luong_khach
        except (ValueError, TypeError):
            so_luong_int = lich_hen.so_luong_khach

        # Kiểm tra sức chứa giường: shampoo tối đa 6 giường, dịch vụ khác (massage) tối đa 30 giường.
        ten_dv_lower = dich_vu_hien_tai.ten_dich_vu.lower()
        is_shampoo = 'shampoo' in ten_dv_lower
        tong_suc_chua = 6 if is_shampoo else 30

        # Lấy các lịch khác cùng ngày (loại trừ Đã hủy, Đã xóa và chính lịch hiện tại).
        query = LichHen.objects.filter(ngay_hen=ngay_str).exclude(trang_thai__in=['Đã hủy', 'Đã xóa']).exclude(ma_lh=lich_hen.ma_lh)

        gio_clean = str(gio_str).strip().lower()
        target_hour_str = gio_clean.split(':')[0] if ':' in gio_clean else '12'

        matched_bookings = []
        for b in query:
            db_time = str(b.gio_hen).lower().strip()
            if target_hour_str in db_time or gio_clean in db_time:
                matched_bookings.append(b)
            elif 'noon' in db_time and target_hour_str == '12':
                matched_bookings.append(b)

        # Cộng tổng số khách đã đặt cùng khung giờ & cùng nhóm phòng (shampoo / massage).
        dat_roi = 0
        for b in matched_bookings:
            is_b_shampoo = 'shampoo' in str(b.ma_dv.ten_dich_vu).lower()
            if is_shampoo and is_b_shampoo:
                dat_roi += b.so_luong_khach
            elif not is_shampoo and not is_b_shampoo:
                dat_roi += b.so_luong_khach

        con_lai = max(0, tong_suc_chua - dat_roi)

        # Nếu số khách mới vượt quá số giường còn trống thì báo lỗi và không lưu.
        if so_luong_int > con_lai:
            loai_phong = "phòng gội riêng (6 giường)" if is_shampoo else "hệ thống phòng massage (30 giường)"
            messages.error(request, f"Không thể đổi lịch! Khung giờ này cho {loai_phong} chỉ còn trống {con_lai} chỗ.")
            return redirect(redirect_url)

        # Cập nhật dịch vụ, ngày hoạt động, giờ, số khách, ghi chú và lưu vào DB.
        if ma_dv_moi:
            lich_hen.ma_dv = dich_vu_hien_tai

        if ngay_hen_moi:
            ngay_hd, _ = NgayHoatDong.objects.get_or_create(
                ngay=ngay_str,
                defaults={'ma_nhd': f'NHD-{ngay_str}', 'trang_thai': 'Mở'}
            )
            lich_hen.ngay_hen = ngay_str
            lich_hen.ma_nhd = ngay_hd

        if gio_hen_moi:
            lich_hen.gio_hen = gio_str

        if so_luong_moi:
            lich_hen.so_luong_khach = so_luong_int
        if ghi_chu_moi is not None:
            lich_hen.ghi_chu = ghi_chu_moi

        lich_hen.save()
        messages.success(request, "Đổi lịch hẹn thành công!")

    return redirect(redirect_url)


# UI: admin_activity_day.html — Quản lý lịch tháng & khóa khoảng ngày hoạt động (chỉ manager).
@manager_only
def manage_activity_days(request):
    today = timezone.localdate()
    try:
        month = int(request.GET.get('month', today.month))
        year = int(request.GET.get('year', today.year))
        if month < 1 or month > 12 or year < 1 or year > 9999:
            raise ValueError
    except (ValueError, TypeError):
        month, year = today.month, today.year

    prev_month, prev_year = (12, year - 1) if month == 1 else (month - 1, year)
    next_month, next_year = (1, year + 1) if month == 12 else (month + 1, year)

    # Dựng ma trận tuần/ngày trong tháng kèm trạng thái đã khóa (True/False) và lý do khóa để hiển thị lịch.
    ngay_khoa_set = set(NgayHoatDong.objects.filter(
        trang_thai='Đã khóa', ngay__year=year, ngay__month=month
    ).values_list('ngay', flat=True))
    cal = calendar.Calendar(firstweekday=0)
    calendar_matrix = []
    for week in cal.monthdatescalendar(year, month):
        week_row = []
        for day in week:
            is_locked = day in ngay_khoa_set
            obj = NgayHoatDong.objects.filter(ngay=day, trang_thai='Đã khóa').first() if is_locked else None
            week_row.append({
                'date': day,
                'day_number': day.day,
                'is_current_month': day.month == month,
                'is_locked': is_locked,
                'ly_do': (obj.ly_do_khoa or '') if obj else '',
            })
        calendar_matrix.append(week_row)

    form = KhoaNgayForm()
    pending_lock = None
    # Xử lý submit form khóa khoảng ngày (btn_khoa_ngay).
    if request.method == 'POST' and 'btn_khoa_ngay' in request.POST:
        form = KhoaNgayForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['ngay_bat_dau']
            end_date = form.cleaned_data['ngay_ket_thuc']
            ly_do = form.cleaned_data['ly_do']
            if ly_do == 'Khác':
                ly_do = (form.cleaned_data.get('nhap_ly_do') or '').strip()

            if not ly_do:
                form.add_error('nhap_ly_do', 'Vui lòng nhập lý do chi tiết.')
            else:
                with transaction.atomic():
                    # Chặn khóa trùng nếu có bất kỳ ngày nào trong khoảng đã 'Đã khóa'.
                    locked = NgayHoatDong.objects.select_for_update().filter(
                        ngay__range=(start_date, end_date), trang_thai='Đã khóa'
                    ).order_by('ngay').first()
                    if locked:
                        form.add_error(None, f'Ngày {locked.ngay:%d/%m/%Y} đã khóa. Vui lòng chọn khoảng khác.')
                    else:
                        # Đếm lịch còn hiệu lực bị ảnh hưởng (không tính hủy/hoàn thành/xóa).
                        affected_count = LichHen.objects.filter(
                            ngay_hen__range=(start_date, end_date)
                        ).exclude(trang_thai__in=['Đã hủy', 'Hoàn thành', 'Đã xóa']).count()
                        # Nếu có lịch bị ảnh hưởng và chưa xác nhận (confirm_affected != '1') thì dừng để hỏi xác nhận.
                        if affected_count and request.POST.get('confirm_affected') != '1':
                            pending_lock = {'count': affected_count}
                            messages.warning(request, f'Có {affected_count} lịch hẹn bị ảnh hưởng. Vui lòng xác nhận trước khi khóa.')
                        else:
                            # Khóa lần lượt từng ngày từ start_date đến end_date.
                            days = (end_date - start_date).days + 1
                            for i in range(days):
                                current_date = start_date + timedelta(days=i)
                                obj, created = NgayHoatDong.objects.get_or_create(
                                    ngay=current_date,
                                    defaults={
                                        'ma_nhd': f'NHD_{current_date:%Y%m%d}_{uuid.uuid4().hex[:6]}',
                                        'trang_thai': 'Đã khóa',
                                        'ly_do_khoa': ly_do,
                                    },
                                )
                                if not created:
                                    obj.trang_thai = 'Đã khóa'
                                    obj.ly_do_khoa = ly_do
                                    obj.save(update_fields=['trang_thai', 'ly_do_khoa'])
                            messages.success(request, f'Đã khóa {days} ngày. {affected_count} lịch hẹn cũ cần được xử lý riêng.' if affected_count else f'Đã khóa {days} ngày thành công.')
                            return redirect('bookings:quan_ly_ngay_hoat_dong')
        else:
            messages.error(request, 'Thông tin khóa ngày chưa hợp lệ. Vui lòng kiểm tra lại.')

    ngay_da_khoa = NgayHoatDong.objects.filter(trang_thai='Đã khóa').order_by('ngay')
    context = {
        'ngay_da_khoa': ngay_da_khoa,
        'form': form,
        'pending_lock': pending_lock,
        'calendar_matrix': calendar_matrix,
        'current_month_year': f'Tháng {month}, {year}',
        'current_month': month,
        'current_year': year,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        **get_staff_context(request),
    }
    return render(request, 'bookings/admin_activity_day.html', context)


# UI: nút mở khóa ngày ở admin_activity_day.html — Mở khóa ngày (chỉ nhận POST, đổi trạng thái về 'Hoạt động').
@manager_only
def unlock_activity_day(request, pk):
    # Thay đổi trạng thái ngày chỉ nhận POST, không cho phép GET.
    if request.method != 'POST':
        return HttpResponseForbidden('Chỉ được mở khóa ngày bằng phương thức POST.')
    ngay_hd = get_object_or_404(NgayHoatDong, pk=pk)
    ngay_hd.trang_thai = 'Hoạt động'
    ngay_hd.ly_do_khoa = None
    ngay_hd.save()
    return redirect('bookings:quan_ly_ngay_hoat_dong')


# UI: JS gọi AJAX khi chọn ngày/giờ/dịch vụ — API trả JSON số giường còn lại (`con_lai`, `tong`).
def api_check_bed_availability(request):
    ngay = request.GET.get('ngay')
    gio = request.GET.get('gio')
    loai_dv = request.GET.get('loai', 'massage')

    if not ngay or not gio:
        return JsonResponse({'con_lai': 30})

    ngay_str = ngay
    if '/' in ngay:
        try:
            ngay_str = datetime.strptime(ngay.strip(), '%d/%m/%Y').date().strftime('%Y-%m-%d')
        except Exception:
            pass

    gio_clean = gio.strip().lower()
    tong_suc_chua = 6 if loai_dv == 'shampoo' else 30

    try:
        all_bookings = LichHen.objects.filter(ngay_hen=ngay_str).exclude(trang_thai__in=['Đã hủy', 'Đã xóa'])

        matched_bookings = []
        target_hour_str = gio_clean.split(':')[0]

        for b in all_bookings:
            db_time = str(b.gio_hen).lower().strip()
            if target_hour_str in db_time or gio_clean in db_time:
                matched_bookings.append(b)
            elif 'noon' in db_time and target_hour_str == '12':
                matched_bookings.append(b)

        # Cộng số khách đã đặt trong khung giờ khớp theo nhóm shampoo (6) hoặc massage (30).
        dat_roi = 0
        for b in matched_bookings:
            is_b_shampoo = 'shampoo' in str(b.ma_dv.ten_dich_vu).lower()
            if loai_dv == 'shampoo' and is_b_shampoo:
                dat_roi += b.so_luong_khach
            elif loai_dv != 'shampoo' and not is_b_shampoo:
                dat_roi += b.so_luong_khach

        con_lai = max(0, tong_suc_chua - dat_roi)
        return JsonResponse({'con_lai': con_lai, 'tong': tong_suc_chua})

    except Exception as e:
        print("Lỗi API kiểm tra giường:", e)
        return JsonResponse({'con_lai': tong_suc_chua, 'tong': tong_suc_chua})


# UI: staff_create.html — Nhân viên/quản lý tạo lịch hẹn hộ khách hàng.
@staff_portal_only
def booking_staff_create(request):
    dich_vu_list = DichVu.objects.all()
    khach_hang_list = KhachHang.objects.select_related('ma_tk__user').all().order_by('-pk')

    locked_dates = list(
        NgayHoatDong.objects.filter(trang_thai='Đã khóa')
        .values_list('ngay', flat=True)
    )
    locked_dates_str = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in locked_dates]

    if request.method == 'POST':
        ma_dv = request.POST.get('ma_dv')
        ngay_hen = request.POST.get('ngay_hen')
        time_slot = request.POST.get('time_slot')
        ho_ten = request.POST.get('ho_ten', '').strip()
        sdt = request.POST.get('sdt', '').strip()
        ma_kh_chon = request.POST.get('ma_kh', '').strip()
        so_luong = request.POST.get('so_luong', 1)
        ghi_chu = request.POST.get('ghi_chu', '')

        try:
            # Kiểm tra hợp lệ: dịch vụ, định dạng ngày dd/mm/yyyy, không đặt ngày quá khứ, giờ hẹn, ngày khóa.
            if not ma_dv:
                messages.error(request, 'Vui lòng chọn dịch vụ trị liệu.')
                return redirect('bookings:staff_booking_create')
            dich_vu = DichVu.objects.filter(pk=ma_dv).first()
            if not dich_vu:
                messages.error(request, 'Dịch vụ đã chọn không hợp lệ. Vui lòng chọn lại.')
                return redirect('bookings:staff_booking_create')

            if not ngay_hen or not ngay_hen.strip():
                messages.error(request, 'Vui lòng chọn ngày hẹn.')
                return redirect('bookings:staff_booking_create')
            try:
                date_obj = datetime.strptime(ngay_hen.strip(), '%d/%m/%Y').date()
            except (ValueError, TypeError):
                messages.error(request, 'Ngày hẹn không đúng định dạng dd/mm/yyyy. Vui lòng chọn lại.')
                return redirect('bookings:staff_booking_create')
            ngay_check = date_obj.strftime('%Y-%m-%d')
            if date_obj < timezone.localdate():
                messages.error(request, 'Không thể đặt lịch vào ngày đã qua.')
                return redirect('bookings:staff_booking_create')
            if not time_slot:
                messages.error(request, 'Vui lòng chọn khung giờ hẹn.')
                return redirect('bookings:staff_booking_create')

            if ngay_check in locked_dates_str:
                messages.error(request, "Ngày bạn chọn hiện đang đóng cửa (Nghỉ lễ/Bảo trì).")
                return redirect('bookings:staff_booking_create')

            # Xác định khách hàng theo ma_kh (đối chiếu khớp SĐT) hoặc tìm theo SĐT tài khoản (không tìm theo họ tên).
            if ma_kh_chon:
                khach_hang = KhachHang.objects.filter(pk=ma_kh_chon).first()
                if khach_hang is None:
                    messages.error(request, 'Khách hàng đã chọn không còn tồn tại. Vui lòng chọn lại.')
                    return redirect('bookings:staff_booking_create')
                so_khach = getattr(getattr(khach_hang, 'ma_tk', None), 'so_dien_thoai', '')
                if so_khach and sdt != so_khach:
                    messages.error(request, 'Số điện thoại không khớp khách hàng đã chọn. Vui lòng chọn lại.')
                    return redirect('bookings:staff_booking_create')
            else:
                if not sdt:
                    messages.error(request, 'Vui lòng chọn khách hàng hoặc nhập số điện thoại.')
                    return redirect('bookings:staff_booking_create')
                khach_hang = KhachHang.objects.filter(ma_tk__so_dien_thoai=sdt).first()
                if khach_hang is None:
                    messages.error(request, 'Không tìm thấy tài khoản khách hàng với số điện thoại này. Vui lòng tạo hồ sơ khách hàng trước khi đặt lịch.')
                    return redirect('bookings:staff_booking_create')

            ngay_hd, _ = NgayHoatDong.objects.get_or_create(
                ngay=ngay_check,
                defaults={'ma_nhd': f'NHD-{ngay_check}', 'trang_thai': 'Mở'}
            )

            ma_lh_moi = f"LH-{random.randint(100000, 999999)}"

            LichHen.objects.create(
                ma_lh=ma_lh_moi,
                ma_kh=khach_hang,
                ma_dv=dich_vu,
                ma_nhd=ngay_hd,
                ngay_hen=ngay_check,
                gio_hen=time_slot,
                so_luong_khach=int(so_luong),
                ghi_chu=ghi_chu,
                trang_thai='Đã đặt'
            )

            messages.success(request, f"Đã tạo thành công lịch hẹn #{ma_lh_moi} cho khách {khach_hang.ho_ten}!")
            return redirect('bookings:staff_booking_list')

        except Exception as e:
            print("LỖI NHÂN VIÊN TẠO LỊCH:", e)
            traceback.print_exc()
            messages.error(request, f"Lỗi tạo lịch: {e}")

    context = {
        'dich_vu_list': dich_vu_list,
        'khach_hang_list': khach_hang_list,
        'locked_dates_json': locked_dates_str,
        **get_staff_context(request)
    }
    return render(request, 'bookings/staff_create.html', context)


# UI: staff_list.html — Danh sách lịch hẹn phía staff/manager, kèm trạng thái phân công nhân viên của từng lịch.
@staff_portal_only
def booking_staff_list(request):
    trang_thai_filter = request.GET.get('trang_thai', '')
    lich_hen_list = (
        LichHen.objects.select_related('ma_dv', 'ma_kh', 'ma_kh__ma_tk', 'ma_nv')
        .exclude(trang_thai='Đã xóa')
        .order_by('-ngay_hen', '-gio_hen')
    )

    if trang_thai_filter == 'active':
        lich_hen_list = lich_hen_list.filter(trang_thai__in=['Đã đặt', 'Đã xác nhận'])
    elif trang_thai_filter == 'completed':
        lich_hen_list = lich_hen_list.filter(trang_thai='Hoàn thành')
    elif trang_thai_filter == 'cancelled':
        lich_hen_list = lich_hen_list.filter(trang_thai='Đã hủy')

    # Truy vấn 1 lần bảng PhanCongLichHen để gom danh sách nhân viên phụ trách cho từng lịch.
    # Tương thích dữ liệu cũ chỉ lưu nhân viên tại LichHen.ma_nv.
    lich_hen_list = list(lich_hen_list)
    assignments_by_booking = {}
    if lich_hen_list:
        assignments = (
            PhanCongLichHen.objects
            .filter(ma_lh_id__in=[lh.pk for lh in lich_hen_list])
            .select_related('ma_nv_phu_trach')
            .order_by('ngay_phan_cong', 'pk')
        )
        for assignment in assignments:
            assignments_by_booking.setdefault(assignment.ma_lh_id, []).append(
                assignment.ma_nv_phu_trach
            )

    # Gắn thông tin nhân viên đã phân công & số nhân viên còn thiếu theo so_luong_khach vào từng object lh.
    for lh in lich_hen_list:
        staff_members = assignments_by_booking.get(lh.pk, [])
        if not staff_members and lh.ma_nv_id:
            staff_members = [lh.ma_nv]
        # Nếu DB có các dòng trùng người, chỉ tính mỗi nhân viên một lần.
        unique_staff = list({str(nv.pk): nv for nv in staff_members}.values())
        lh.staff_assignees = unique_staff
        lh.staff_assignees_count = len(unique_staff)
        lh.staff_assignees_names = ' | '.join(nv.ho_ten for nv in unique_staff)
        lh.staff_assignees_missing = max(0, (lh.so_luong_khach or 1) - len(unique_staff))
        lh.staff_fully_assigned = lh.staff_assignees_missing == 0

    # Dữ liệu dành cho popup Đổi lịch ở staff_list.html
    dich_vu_list = DichVu.objects.all()
    locked_dates = NgayHoatDong.objects.filter(
        trang_thai='Đã khóa'
    ).values_list('ngay', flat=True)
    locked_dates_json = json.dumps([
        d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)
        for d in locked_dates
    ])

    return render(request, 'bookings/staff_list.html', {
        'lich_hen_list': lich_hen_list,
        'dich_vu_list': dich_vu_list,
        'locked_dates_json': locked_dates_json,
        'current_filter': trang_thai_filter,
        **get_staff_context(request)
    })


# UI: staff_detail.html — Chi tiết lịch hẹn phía staff/manager, chuẩn bị danh sách nhân viên & các ô phân công theo số khách.
@staff_portal_only
def booking_staff_detail(request, ma_lh):
    lich_hen = get_object_or_404(
        LichHen.objects.select_related('ma_dv', 'ma_kh', 'ma_nv').exclude(trang_thai='Đã xóa'), ma_lh=ma_lh
    )
    dich_vu_list = DichVu.objects.all()
    # Chỉ nhân viên nghiệp vụ (ROLE_STAFF) đang hoạt động mới được chọn phục vụ khách.
    danh_sach_nhan_vien = (
        NhanVien.objects.filter(ma_tk__vai_tro=ROLE_STAFF, ma_tk__user__is_active=True)
        .order_by('ho_ten', 'pk')
    )

    # Lấy danh sách nhân viên đã phân công (từ PhanCongLichHen, fallback LichHen.ma_nv).
    phan_cong_list = list(
        PhanCongLichHen.objects.filter(ma_lh=lich_hen)
        .select_related('ma_nv_phu_trach')
        .order_by('ngay_phan_cong', 'pk')
    )
    ds_da_chon = [pc.ma_nv_phu_trach for pc in phan_cong_list]
    if not ds_da_chon and lich_hen.ma_nv_id:
        ds_da_chon = [lich_hen.ma_nv]

    # Tạo danh sách o_phan_cong đúng bằng so_khach để render số dropdown chọn nhân viên tương ứng.
    so_khach = max(1, lich_hen.so_luong_khach or 1)
    o_phan_cong = [
        {'stt': idx + 1,
         'nhan_vien_id': str(ds_da_chon[idx].pk) if idx < len(ds_da_chon) else ''}
        for idx in range(so_khach)
    ]

    return render(request, 'bookings/staff_detail.html', {
        'lich_hen': lich_hen,
        'dich_vu_list': dich_vu_list,
        'danh_sach_nhan_vien': danh_sach_nhan_vien,
        'nhan_vien_da_phan_cong': ds_da_chon,
        'o_phan_cong': o_phan_cong,
        'so_nhan_vien_da_phan_cong': len(ds_da_chon),
        'locked_dates_json': json.dumps([d.strftime('%Y-%m-%d') for d in NgayHoatDong.objects.filter(trang_thai='Đã khóa').values_list('ngay', flat=True)]),
        'spa_closed': NgayHoatDong.objects.filter(ngay=lich_hen.ngay_hen, trang_thai='Đã khóa').exists(),
        **get_staff_context(request)
    })


# UI: nút/modal Hủy lịch & Hoàn thành lịch ở staff_detail.html — Xử lý hủy lịch hoặc hoàn thành lịch + cộng điểm loyalty.
@staff_portal_only
def booking_staff_complete(request, ma_lh):
    """Xử lý hoàn thành lịch (kèm cộng điểm) hoặc hủy lịch từ portal nhân viên."""
    if request.method != 'POST':
        return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)

    # 1. Nhánh HỦY LỊCH từ modal nhân viên (booking_action == 'cancel').
    if request.POST.get('booking_action') == 'cancel':
        with transaction.atomic():
            lich_hen = get_object_or_404(LichHen.objects.select_for_update(), ma_lh=ma_lh)
            if lich_hen.trang_thai in ('Đã hủy', 'Hoàn thành', 'Đã xóa'):
                messages.error(request, 'Lịch đã kết thúc hoặc hủy, không thể thao tác.')
                return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)

            # Kiểm tra lý do hủy; riêng lý do 'Spa đóng cửa' chỉ hợp lệ khi ngày hẹn đang bị khóa.
            ly_do = (request.POST.get('ly_do_huy') or '').strip()
            if ly_do == 'Khác':
                ly_do = (request.POST.get('ly_do_khac') or '').strip()
            if not ly_do:
                messages.error(request, 'Vui lòng chọn hoặc nhập lý do hủy lịch.')
                return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)

            spa_closed = NgayHoatDong.objects.filter(
                ngay=lich_hen.ngay_hen, trang_thai='Đã khóa'
            ).exists()
            if ly_do == 'Spa đóng cửa' and not spa_closed:
                messages.error(request, 'Chỉ có thể chọn lý do Spa đóng cửa khi ngày hẹn đã bị khóa.')
                return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)

            # Lịch thường phải hủy trước giờ hẹn ít nhất 6 tiếng (trừ trường hợp Spa đóng cửa).
            appointment_dt = datetime.combine(lich_hen.ngay_hen, lich_hen.gio_hen)
            if timezone.is_naive(appointment_dt):
                appointment_dt = timezone.make_aware(appointment_dt, timezone.get_current_timezone())
            if not (spa_closed and ly_do == 'Spa đóng cửa') and appointment_dt - timezone.now() < timedelta(hours=6):
                messages.error(request, 'Không thể hủy: lịch thông thường phải hủy trước giờ hẹn ít nhất 6 tiếng.')
                return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)

            lich_hen.trang_thai = 'Đã hủy'
            lich_hen.ly_do_huy = ly_do
            lich_hen.save(update_fields=['trang_thai', 'ly_do_huy'])
            messages.success(request, f'Đã hủy lịch #{lich_hen.ma_lh} thành công.')
        return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)

    # 2. Nhánh HOÀN THÀNH LỊCH: kiểm tra đã hết thời lượng dịch vụ -> cập nhật Hoàn thành -> cộng điểm & gửi thông báo.
    from customers.loyalty import cong_diem_khi_hoan_thanh
    from notifications.loyalty import tao_thong_bao_tich_diem

    try:
        with transaction.atomic():
            lich_hen = get_object_or_404(
                LichHen.objects.select_for_update(), ma_lh=ma_lh
            )

            if lich_hen.trang_thai in ('Đã hủy', 'Đã xóa'):
                messages.error(request, 'Lịch đã hủy hoặc xóa không thể hoàn thành.')
                return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)

            if lich_hen.trang_thai == 'Hoàn thành':
                messages.info(request, 'Lịch này đã hoàn thành trước đó.')
                return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)

            # Chặn hoàn thành sớm: thời điểm hiện tại phải sau (gio_hen + _thoi_luong_phut).
            bat_dau = datetime.combine(lich_hen.ngay_hen, lich_hen.gio_hen)
            if timezone.is_naive(bat_dau):
                bat_dau = timezone.make_aware(bat_dau, timezone.get_current_timezone())
            ket_thuc = bat_dau + timedelta(minutes=_thoi_luong_phut(lich_hen))
            if timezone.now() < ket_thuc:
                messages.error(
                    request,
                    'Chưa thể hoàn thành lịch hẹn! Dịch vụ dự kiến kết thúc lúc '
                    f'{timezone.localtime(ket_thuc):%H:%M ngày %d/%m/%Y}.'
                )
                return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)

            lich_hen.trang_thai = 'Hoàn thành'
            lich_hen.save(update_fields=['trang_thai'])

            # Cộng điểm tích lũy và tạo thông báo cho khách (lỗi sẽ rollback cả trạng thái Hoàn thành).
            ket_qua = cong_diem_khi_hoan_thanh(lich_hen.ma_lh)
            if not ket_qua.get('success'):
                raise ValueError(ket_qua.get('message') or 'Không cộng được điểm.')

            tao_thong_bao_tich_diem(lich_hen.ma_lh, ket_qua)

            diem = ket_qua['diem_cong']
            thong_bao = (
                f"Đã cập nhật lịch hẹn #{lich_hen.ma_lh} thành Hoàn thành "
                f"và cộng {diem} điểm tích lũy!"
            )
            if ket_qua.get('len_hang'):
                thong_bao += f" Khách đã lên hạng {ket_qua['hang_moi']}!"

            messages.success(request, thong_bao)
    except Exception:
        traceback.print_exc()
        messages.error(
            request,
            'Không thể hoàn thành lịch và cộng điểm. Dữ liệu chưa thay đổi; '
            'vui lòng kiểm tra cấu hình điểm và thử lại.'
        )

    return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)


# UI: modal xóa lịch ở staff_detail.html — Xóa mềm lịch hẹn (chuyển trạng thái 'Đã xóa' + lưu lý do, chỉ manager).
@manager_only
def booking_admin_delete(request, ma_lh):
    if request.method == "POST":
        lich_hen = get_object_or_404(LichHen, ma_lh=ma_lh)
        ma_hien_tai = lich_hen.ma_lh
        # Kiểm tra lý do xóa thuộc danh sách cho phép (nếu chọn 'Khác' thì lấy ly_do_xoa_khac).
        ly_do_xoa = (request.POST.get('ly_do_xoa') or '').strip()
        if ly_do_xoa not in ('Lịch tạo nhầm', 'Lịch bị trùng', 'Spa không thể phục vụ', 'Khác'):
            messages.error(request, 'Vui lòng chọn lý do xóa lịch hợp lệ.')
            return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)
        if ly_do_xoa == 'Khác':
            ly_do_xoa = (request.POST.get('ly_do_xoa_khac') or '').strip()
            if not ly_do_xoa:
                messages.error(request, 'Vui lòng nhập lý do xóa lịch.')
                return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)
        lich_hen.trang_thai = 'Đã xóa'
        lich_hen.ly_do_huy = ly_do_xoa
        lich_hen.save()
        messages.success(request, f"Đã xóa lịch hẹn #{ma_hien_tai} khỏi danh sách quản lý thành công.")

    return redirect('bookings:staff_booking_list')


# Hàm phụ tách số phút từ trường thoi_luong của dịch vụ (mặc định 150 phút nếu không đọc được).
def _thoi_luong_phut(lich_hen):
    """Đọc số phút từ thoi_luong (int, Decimal hoặc chuỗi '150 phút')."""
    value = getattr(lich_hen.ma_dv, 'thoi_luong', None)
    matched = re.search(r'\d+', str(value or ''))
    return max(1, int(matched.group())) if matched else 150


# Hàm phụ kiểm tra nhân viên chọn có bị trùng khoảng thời gian phục vụ [bắt đầu, kết thúc) với lịch khác không.
def _trung_ca_lam(lich_hen, nhan_vien_ids):
    """Kiểm tra giao nhau của khoảng [bắt đầu, kết thúc), kể cả lịch cũ."""
    bat_dau = datetime.combine(lich_hen.ngay_hen, lich_hen.gio_hen)
    ket_thuc = bat_dau + timedelta(minutes=_thoi_luong_phut(lich_hen))
    trang_thai_bo_qua = ['Đã hủy', 'Đã xóa', 'Hoàn thành']

    # 1. Kiểm tra trên các lịch đã phân công trong bảng PhanCongLichHen.
    pc_qs = (PhanCongLichHen.objects
             .select_related('ma_lh__ma_dv', 'ma_nv_phu_trach')
             .filter(ma_lh__ngay_hen=lich_hen.ngay_hen,
                     ma_nv_phu_trach_id__in=nhan_vien_ids)
             .exclude(ma_lh=lich_hen)
             .exclude(ma_lh__trang_thai__in=trang_thai_bo_qua))
    for pc in pc_qs:
        other = pc.ma_lh
        other_start = datetime.combine(other.ngay_hen, other.gio_hen)
        other_end = other_start + timedelta(minutes=_thoi_luong_phut(other))
        if bat_dau < other_end and other_start < ket_thuc:
            return pc.ma_nv_phu_trach.ho_ten, other.ma_lh

    # 2. Kiểm tra trên các lịch cũ chỉ lưu 1 nhân viên trực tiếp ở cột LichHen.ma_nv.
    old_qs = (LichHen.objects.select_related('ma_dv', 'ma_nv')
              .filter(ngay_hen=lich_hen.ngay_hen, ma_nv_id__in=nhan_vien_ids)
              .exclude(ma_lh=lich_hen.ma_lh)
              .exclude(trang_thai__in=trang_thai_bo_qua))
    for other in old_qs:
        other_start = datetime.combine(other.ngay_hen, other.gio_hen)
        other_end = other_start + timedelta(minutes=_thoi_luong_phut(other))
        if bat_dau < other_end and other_start < ket_thuc:
            return other.ma_nv.ho_ten, other.ma_lh
    return None


# UI: form phân công nhân viên ở staff_detail.html — Gán đủ nhân viên theo số khách hoặc hủy toàn bộ phân công (chỉ manager).
@manager_only
def assign_staff_to_booking(request, ma_lh):
    if request.method != 'POST':
        return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)

    with transaction.atomic():
        lich_hen = get_object_or_404(
            LichHen.objects.select_for_update().select_related('ma_dv'), ma_lh=ma_lh
        )
        if lich_hen.trang_thai in ('Đã hủy', 'Đã xóa', 'Hoàn thành'):
            messages.error(request, 'Lịch đã kết thúc hoặc hủy, không thể phân công.')
            return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)

        # Nút 'Hủy toàn bộ phân công' (clear_assignment == '1'): xóa sạch bản ghi phân công và gỡ ma_nv.
        if request.POST.get('clear_assignment') == '1':
            PhanCongLichHen.objects.filter(ma_lh=lich_hen).delete()
            lich_hen.ma_nv = None
            lich_hen.save(update_fields=['ma_nv'])
            messages.success(request, 'Đã hủy toàn bộ phân công nhân viên.')
            return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)

        # Kiểm tra chọn đủ số nhân viên bằng so_luong_khach và không chọn trùng cùng 1 nhân viên.
        selected_ids = [v.strip() for v in request.POST.getlist('nhan_vien_ids')]
        so_khach = max(1, lich_hen.so_luong_khach or 1)
        if len(selected_ids) != so_khach or any(not v for v in selected_ids):
            messages.error(request, f'Lịch có {so_khach} khách: phải chọn đủ {so_khach} nhân viên.')
            return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)
        if len(set(selected_ids)) != len(selected_ids):
            messages.error(request, 'Không thể chọn cùng một nhân viên cho nhiều khách trong một lịch.')
            return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)

        # Chỉ cho phép nhân viên có vai trò ROLE_STAFF và tài khoản đang kích hoạt (is_active=True).
        nhan_vien = list(NhanVien.objects.filter(
            pk__in=selected_ids,
            ma_tk__vai_tro=ROLE_STAFF,
            ma_tk__user__is_active=True,
        ))
        by_id = {str(nv.pk): nv for nv in nhan_vien}
        if len(by_id) != len(selected_ids):
            messages.error(request, 'Chỉ được phân công nhân viên có tài khoản đang hoạt động. Vui lòng chọn lại.')
            return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)

        # Chặn phân công nếu có nhân viên bị trùng giờ với lịch hẹn khác trong ngày.
        trung = _trung_ca_lam(lich_hen, selected_ids)
        if trung:
            ten_nv, ma_lh_trung = trung
            messages.error(request, f'Nhân viên {ten_nv} đã có lịch #{ma_lh_trung} trùng thời gian phục vụ.')
            return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)

        # Lấy hồ sơ TaiKhoan của quản lý đang thao tác để lưu vào ma_nv_phan_cong.
        nguoi_phan_cong = TaiKhoan.objects.filter(user=request.user).first()
        if not nguoi_phan_cong:
            messages.error(request, 'Tài khoản đang đăng nhập chưa có hồ sơ TaiKhoan để ghi nhận người phân công.')
            return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)

        # Xóa phân công cũ và tạo mới danh sách PhanCongLichHen; đồng bộ ma_nv là người đầu tiên.
        PhanCongLichHen.objects.filter(ma_lh=lich_hen).delete()
        PhanCongLichHen.objects.bulk_create([
            PhanCongLichHen(
                ma_pclh='PC-' + uuid.uuid4().hex[:16].upper(),
                ma_lh=lich_hen,
                ma_nv_phu_trach=by_id[nv_id],
                ma_nv_phan_cong=nguoi_phan_cong,
            )
            for nv_id in selected_ids
        ])
        # Giữ ma_nv là người thứ nhất để không hỏng phần hiển thị/code cũ.
        lich_hen.ma_nv = by_id[selected_ids[0]]
        lich_hen.save(update_fields=['ma_nv'])

    messages.success(request, f'Đã phân công đủ {so_khach} nhân viên cho lịch #{ma_lh}.')
    return redirect('bookings:staff_booking_detail', ma_lh=ma_lh)


# ============================================================================
# [BỔ SUNG] KẾT NỐI ƯU ĐÃI VỚI BOOKING KHÁCH HÀNG
# Toàn bộ các hàm Booking ở trên được giữ nguyên, không sửa logic cũ.
# Phần dưới bọc thêm luồng ưu đãi quanh booking_customer_create.
# ============================================================================

# Kiểm tra mã ưu đãi (GET ?promo= hoặc POST promo_id) có hợp lệ về trạng thái, hạn, dịch vụ, ngày hẹn, hạng TV và giá không.
def _promo_hop_le_cho_booking(request, promo_code=None, service_id=None, ngay_hen=None):
    """Xác thực ưu đãi từ database; nếu không có mã thì không áp dụng."""
    from notifications.models import ChuongTrinhUuDai

    if promo_code is None:
        promo_code = (request.GET.get('promo') or '').strip()
    if not promo_code:
        return None

    promo = (ChuongTrinhUuDai.objects
             .select_related('ma_dv')
             .filter(pk=promo_code).first())
    if not promo or not promo.ma_dv_id:
        raise ValueError('Ưu đãi không tồn tại hoặc chưa liên kết dịch vụ.')

    hien_tai = timezone.now()
    if (promo.trang_thai != 'Đang áp dụng'
            or promo.ngay_bat_dau > hien_tai
            or promo.ngay_ket_thuc < hien_tai):
        raise ValueError('Chương trình ưu đãi hiện không còn hiệu lực.')

    if service_id is not None and str(promo.ma_dv_id) != str(service_id):
        raise ValueError('Dịch vụ đã chọn không khớp với dịch vụ được ưu đãi.')

    # Không cho khách đặt ngày nằm ngoài đợt ưu đãi đã công bố.
    if ngay_hen is not None:
        if not (timezone.localtime(promo.ngay_bat_dau).date()
                <= ngay_hen <= timezone.localtime(promo.ngay_ket_thuc).date()):
            raise ValueError('Ngày hẹn nằm ngoài thời gian áp dụng ưu đãi.')

    # Quyền sử dụng ưu đãi phải được kiểm tra trên server.
    doi_tuong = (promo.doi_tuong_ap_dung or '').strip().lower()
    if doi_tuong not in ('', 'tất cả khách hàng', 'tat ca khach hang'):
        khach_hang = (KhachHang.objects
                      .select_related('ma_tv')
                      .filter(ma_tk__user=request.user).first())
        hang = ''
        if khach_hang and khach_hang.ma_tv_id:
            hang = (khach_hang.ma_tv.ten_hang or '').strip().lower()
        if not hang or hang not in doi_tuong:
            raise ValueError('Hạng thành viên của bạn không thuộc đối tượng ưu đãi.')

    # Giá ưu đãi được tính lại từ model, không tin giá gửi từ client.
    gia_moi = promo.tinh_gia_uu_dai()
    if gia_moi <= 0 or gia_moi > promo.ma_dv.gia_dich_vu:
        raise ValueError('Giá ưu đãi không hợp lệ, vui lòng liên hệ spa.')

    return promo


# Lưu tham chiếu hàm đặt lịch gốc trước khi bọc thêm xử lý ưu đãi.
_booking_customer_create_goc = booking_customer_create


# UI: customer_create.html (khi có ?promo= hoặc promo_id) — Tạo lịch và lưu LichHenUuDai trong cùng 1 transaction.
@login_required(login_url='/accounts/dang_nhap/')
@wraps(_booking_customer_create_goc)
def booking_customer_create(request, *args, **kwargs):
    """Chỉ thêm luồng ưu đãi; đặt lịch không có mã ưu đãi vẫn chạy hàm gốc như cũ."""
    from notifications.models import LichHenUuDai

    # GET: gọi hàm gốc (kèm promo_ap_dung); nếu mã ưu đãi trên URL không hợp lệ thì báo cảnh báo và quay về danh sách ưu đãi.
    if request.method != 'POST':
        try:
            return _booking_customer_create_goc(request, *args, **kwargs)
        except ValueError as exc:
            messages.warning(request, str(exc))
            return redirect('notifications:danh_sach_uu_dai')

    # POST không gửi promo_id: chạy thẳng hàm đặt lịch gốc.
    promo_code = (request.POST.get('promo_id') or '').strip()
    if not promo_code:
        return _booking_customer_create_goc(request, *args, **kwargs)

    # POST có promo_id: kiểm tra lại toàn bộ điều kiện ưu đãi trên server trước khi tạo lịch.
    try:
        raw_date = (request.POST.get('ngay_hen') or '').strip()
        if '/' in raw_date:
            ngay_dat = datetime.strptime(raw_date, '%d/%m/%Y').date()
        else:
            ngay_dat = datetime.strptime(raw_date, '%Y-%m-%d').date()

        so_luong = int(request.POST.get('so_luong', '1'))
        if not 1 <= so_luong <= 10:
            raise ValueError('Số lượng khách phải từ 1 đến 10.')

        promo = _promo_hop_le_cho_booking(
            request,
            promo_code=promo_code,
            service_id=request.POST.get('ma_dv'),
            ngay_hen=ngay_dat,
        )
        if promo is None:
            raise ValueError('Không xác định được chương trình ưu đãi.')

        # Transaction bọc cả tạo LichHen và LichHenUuDai; có lỗi thì rollback DB và xóa mã tạm trong session.
        try:
            with transaction.atomic():
                response = _booking_customer_create_goc(request, *args, **kwargs)
                success_url = reverse('bookings:booking_customer_success')
                if (response.status_code != 302
                        or response.get('Location', '').split('?', 1)[0] != success_url):
                    return response

                ma_lh = request.session.get('last_booking_code')
                lich_hen = LichHen.objects.filter(
                    pk=ma_lh,
                    ma_kh__ma_tk__user=request.user,
                    ma_dv_id=promo.ma_dv_id,
                    so_luong_khach=so_luong,
                    ngay_hen=ngay_dat,
                ).first()
                if lich_hen is None:
                    raise ValueError('Không tìm thấy lịch hẹn vừa tạo để gắn ưu đãi.')

                # Lưu tổng giá gốc và tổng giá sau giảm theo số khách tại thời điểm đặt.
                LichHenUuDai.objects.create(
                    ma_lh=lich_hen,
                    ma_ctud=promo,
                    gia_goc=promo.ma_dv.gia_dich_vu * so_luong,
                    gia_sau_giam=promo.tinh_gia_uu_dai() * so_luong,
                )
                return response
        except Exception:
            # Session nằm ngoài transaction DB nên cần xóa thủ công khi lỗi xảy ra.
            request.session.pop('last_booking_code', None)
            raise
    except (ValueError, TypeError) as exc:
        messages.error(request, str(exc))
    except Exception:
        traceback.print_exc()
        messages.error(request, 'Không thể lưu ưu đãi cho lịch hẹn. Vui lòng thử lại.')

    # Giữ ?promo= trên URL để khách không phải chọn lại ưu đãi khi thao tác lại.
    return redirect(reverse('bookings:booking_customer_create') + '?promo=' + promo_code)



# ============================================================================
# [BỔ SUNG] ĐỒNG BỘ ƯU ĐÃI KHI ĐỔI LỊCH - CÓ XÁC NHẬN MẤT ƯU ĐÃI
# Các hàm Booking gốc ở trên giữ nguyên, chỉ bọc thêm xử lý quanh hàm đổi lịch.
# Quy ước: gia_goc == gia_sau_giam nghĩa là ưu đãi không còn áp dụng;
# ma_ctud vẫn giữ để lưu vết lịch từng dùng chương trình nào.
# ============================================================================

from decimal import Decimal, ROUND_HALF_UP
from django.core import signing
from django.core.signing import BadSignature, SignatureExpired

_booking_customer_reschedule_goc = booking_customer_reschedule
_PROMO_CONFIRM_SALT = 'charmspa-reschedule-promo-v1'


# Chuẩn hóa giá trị ngày (date, datetime hoặc chuỗi) về kiểu date.
def _ngay_booking(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


# Làm tròn số tiền về 2 chữ số thập phân bằng Decimal.
def _tien_booking(value):
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


# UI: modal đổi lịch + trang bookings/confirm_promotion_change.html — Tính lại giá ưu đãi và xin xác nhận nếu đổi lịch làm mất ưu đãi.
@login_required(login_url='/accounts/dang_nhap/')
@wraps(_booking_customer_reschedule_goc)
def booking_customer_reschedule(request, ma_lh):
    """Chạy hàm đổi lịch gốc và đồng bộ giá ưu đãi trong cùng một transaction."""
    from notifications.models import LichHenUuDai

    if request.method != 'POST':
        return _booking_customer_reschedule_goc(request, ma_lh)

    redirect_url = (
        'bookings:staff_booking_list'
        if request.user.is_staff or request.user.is_superuser
        else 'bookings:booking_customer_list'
    )
    qs = LichHen.objects.filter(ma_lh=ma_lh)
    if not (request.user.is_staff or request.user.is_superuser):
        qs = qs.filter(ma_kh__ma_tk__user=request.user)

    # Kiểm tra bắt buộc có ngày/giờ mới cho cả lịch thường và lịch ưu đãi trước khi gọi hàm gốc.
    if not (request.POST.get('ngay_hen_moi') or '').strip():
        messages.error(request, 'Vui lòng chọn ngày hẹn mới.')
        return redirect(redirect_url)
    if not (request.POST.get('gio_hen_moi') or '').strip():
        messages.error(request, 'Vui lòng chọn khung giờ hẹn mới.')
        return redirect(redirect_url)

    # Nếu lịch không gắn bản ghi ưu đãi thì giao thẳng cho hàm đổi lịch gốc xử lý.
    if not qs.filter(uu_dai_ap_dung__isnull=False).exists():
        return _booking_customer_reschedule_goc(request, ma_lh)

    try:
        with transaction.atomic():
            lich = get_object_or_404(qs.select_for_update(), ma_lh=ma_lh)
            item = (LichHenUuDai.objects.select_for_update()
                    .select_related('ma_ctud').get(ma_lh=lich))
            chuong_trinh = item.ma_ctud

            ngay_cu = _ngay_booking(lich.ngay_hen)
            ngay_nhap = (request.POST.get('ngay_hen_moi') or '').strip()
            try:
                ngay_moi = (
                    datetime.strptime(ngay_nhap, '%d/%m/%Y' if '/' in ngay_nhap else '%Y-%m-%d').date()
                    if ngay_nhap else ngay_cu
                )
            except (ValueError, TypeError):
                raise ValueError('Ngày hẹn mới không hợp lệ.')

            ma_dv_moi = (request.POST.get('ma_dv_moi') or '').strip() or str(lich.ma_dv_id)
            dv_moi = DichVu.objects.filter(pk=ma_dv_moi).first()
            if dv_moi is None:
                raise ValueError('Dịch vụ mới không tồn tại.')

            so_cu = int(lich.so_luong_khach)
            if so_cu < 1:
                raise ValueError('Số khách trong lịch cũ không hợp lệ.')
            so_nhap = (request.POST.get('so_luong_khach_moi') or '').strip()
            try:
                so_moi = int(so_nhap) if so_nhap else so_cu
            except (ValueError, TypeError):
                raise ValueError('Số lượng khách phải là số nguyên.')
            if not 1 <= so_moi <= 10:
                raise ValueError('Số lượng khách phải từ 1 đến 10.')

            # Kiểm tra đổi lịch có làm mất ưu đãi không (đổi dịch vụ, hoặc đổi ngày ra ngoài hạn/chương trình tạm dừng).
            da_co_giam = item.gia_sau_giam < item.gia_goc
            doi_dich_vu = str(lich.ma_dv_id) != str(ma_dv_moi)
            doi_ngay = ngay_moi != ngay_cu
            con_trong_ngay = (
                timezone.localtime(chuong_trinh.ngay_bat_dau).date()
                <= ngay_moi
                <= timezone.localtime(chuong_trinh.ngay_ket_thuc).date()
            )
            tam_dung = chuong_trinh.trang_thai in ('Tạm dừng', 'Ngừng áp dụng')
            mat_uu_dai = da_co_giam and (
                doi_dich_vu or (doi_ngay and (not con_trong_ngay or tam_dung))
            )

            # Còn ưu đãi thì tính lại theo đơn giá ưu đãi cũ; mất ưu đãi thì đưa về giá gốc dịch vụ mới.
            if da_co_giam and not mat_uu_dai:
                gia_goc_moi = _tien_booking(item.gia_goc * Decimal(so_moi) / Decimal(so_cu))
                gia_sau_moi = _tien_booking(item.gia_sau_giam * Decimal(so_moi) / Decimal(so_cu))
            else:
                gia_goc_moi = _tien_booking(dv_moi.gia_dich_vu * so_moi)
                gia_sau_moi = gia_goc_moi

            # Nếu đổi lịch làm mất ưu đãi và chưa có token xác nhận khớp dữ liệu -> mở trang xác nhận cho khách.
            if mat_uu_dai:
                expected = {
                    'booking': str(lich.pk),
                    'user': str(request.user.pk),
                    'old_service': str(lich.ma_dv_id),
                    'old_date': ngay_cu.isoformat(),
                    'old_guests': so_cu,
                    'old_base': str(item.gia_goc),
                    'old_total': str(item.gia_sau_giam),
                    'new_service': str(ma_dv_moi),
                    'new_date': ngay_moi.isoformat(),
                    'new_guests': so_moi,
                    'new_total': str(gia_sau_moi),
                    'new_time': (request.POST.get('gio_hen_moi') or ''),
                    'notes': (request.POST.get('ghi_chu_moi') or ''),
                }
                confirm_token = request.POST.get('promo_confirm_token') or ''
                confirmed = False
                if confirm_token:
                    try:
                        confirmed = (
                            signing.loads(confirm_token, salt=_PROMO_CONFIRM_SALT, max_age=600)
                            == expected
                        )
                    except (BadSignature, SignatureExpired):
                        confirmed = False
                if not confirmed:
                    token = signing.dumps(expected, salt=_PROMO_CONFIRM_SALT)
                    return render(request, 'bookings/confirm_promotion_change.html', {
                        'lich_hen': lich,
                        'ten_dich_vu_moi': dv_moi.ten_dich_vu,
                        'ngay_moi': ngay_moi,
                        'so_khach_moi': so_moi,
                        'gia_cu': item.gia_sau_giam,
                        'gia_moi': gia_sau_moi,
                        'confirm_token': token,
                        'post_fields': {
                            k: request.POST.get(k, '') for k in (
                                'ngay_hen_moi', 'gio_hen_moi', 'ma_dv_moi',
                                'so_luong_khach_moi', 'ghi_chu_moi',
                            )
                        },
                        'cancel_url': reverse('bookings:booking_customer_detail', args=[lich.pk])
                        if not (request.user.is_staff or request.user.is_superuser)
                        else reverse('bookings:staff_booking_detail', args=[lich.pk]),
                    })

            # Gọi hàm đổi lịch gốc để kiểm tra điều kiện (3 tiếng, ngày khóa, sức chứa) và lưu LichHen.
            response = _booking_customer_reschedule_goc(request, ma_lh)
            lich.refresh_from_db()
            ngay_luu = _ngay_booking(lich.ngay_hen)
            gio_moi = (request.POST.get('gio_hen_moi') or '').strip()
            gio_luu = str(lich.gio_hen)[:5]
            # Nếu hàm gốc không đổi được lịch thì giữ nguyên bản ghi ưu đãi hiện tại.
            if (ngay_luu != ngay_moi
                    or str(lich.ma_dv_id) != str(ma_dv_moi)
                    or int(lich.so_luong_khach) != so_moi
                    or (gio_moi and gio_luu != gio_moi[:5])):
                return response

            # Cập nhật lại gia_goc và gia_sau_giam trong LichHenUuDai sau khi đổi lịch thành công.
            if item.gia_goc != gia_goc_moi or item.gia_sau_giam != gia_sau_moi:
                item.gia_goc = gia_goc_moi
                item.gia_sau_giam = gia_sau_moi
                item.save(update_fields=['gia_goc', 'gia_sau_giam'])
            if mat_uu_dai:
                messages.info(request,
                    'Lịch hẹn đã được đổi với giá thông thường; ưu đãi cũ không còn áp dụng.')
            return response
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect(redirect_url)
    except Exception:
        traceback.print_exc()
        messages.error(request, 'Không cập nhật được giá khi đổi lịch. Vui lòng thử lại.')
        return redirect(redirect_url)