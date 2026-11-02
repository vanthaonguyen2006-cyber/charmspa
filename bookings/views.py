import calendar
import json
import random
import traceback
import uuid
from datetime import date, datetime, timedelta
from customers.models import KhachHang
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from services.models import DichVu
from .forms import KhoaNgayForm
from .models import LichHen, NgayHoatDong
from accounts.models import NhanVien, TaiKhoan


def is_admin(user):
    """Cho phép quản trị viên và nhân viên nội bộ thao tác quản lý lịch."""
    return user.is_authenticated and (user.is_superuser or user.is_staff)


def get_staff_context(request):
    """Hàm phụ trợ lấy thông tin hiển thị tên tài khoản (Phân biệt rõ Admin/Staff và Khách hàng)"""
    name = request.user.username if request.user.is_authenticated else "Tài khoản"

    # Kiểm tra xem user có phải là Admin hoặc Nhân viên nội bộ hay không
    is_admin_or_staff = request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff)

    if is_admin_or_staff:
        position = "Quản trị viên" if request.user.is_superuser else "Nhân viên"
    else:
        position = "Khách hàng"
        # Chỉ check bảng KhachHang nếu đây là tài khoản khách hàng thực sự (không phải admin/staff)
        if request.user.is_authenticated:
            try:
                kh = KhachHang.objects.filter(ma_tk__user=request.user).first()
                if kh and kh.ho_ten:
                    name = kh.ho_ten
            except Exception:
                pass

    initials = name[:2].upper() if name else '?'
    return {
        'staff_name': name,
        'staff_initials': initials,
        'staff_position': position,
    }


@login_required(login_url='/accounts/dang_nhap/')
def booking_customer_create(request):
    """Chỉ tài khoản khách hàng đã đăng nhập mới được đặt lịch từ trang khách."""
    if request.user.is_staff or request.user.is_superuser:
        return HttpResponseForbidden("Vui lòng dùng chức năng tạo lịch hẹn của nhân viên.")

    if not TaiKhoan.objects.filter(user=request.user, vai_tro='Khách hàng').exists():
        return HttpResponseForbidden("Chỉ tài khoản có vai trò Khách hàng mới được đặt lịch.")

    dich_vu_list = DichVu.objects.all()

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

            ngay_check = datetime.today().strftime('%Y-%m-%d')
            if ngay_hen:
                if '/' in ngay_hen:
                    date_obj = datetime.strptime(ngay_hen.strip(), '%d/%m/%Y').date()
                else:
                    date_obj = datetime.strptime(ngay_hen.strip(), '%Y-%m-%d').date()
                ngay_check = date_obj.strftime('%Y-%m-%d')

            if ngay_check in locked_dates_str:
                messages.error(request, "Ngày bạn chọn hiện đang đóng cửa (Nghỉ lễ/Bảo trì). Vui lòng chọn ngày khác.")
                return redirect('booking_customer_create')

            so_luong_int = int(so_luong) if so_luong else 1

            tai_khoan_Obj = TaiKhoan.objects.get(user=request.user)

            khach_hang, _ = KhachHang.objects.get_or_create(
                ma_tk=tai_khoan_Obj,
                defaults={'ho_ten': ho_ten}
            )
            if ho_ten and khach_hang.ho_ten != ho_ten:
                khach_hang.ho_ten = ho_ten
                khach_hang.save()

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
                so_luong_khach=so_luong_int,
                ghi_chu=ghi_chu,
                trang_thai='Đã đặt'
            )

            request.session['last_booking_code'] = ma_lh_moi
            return redirect('booking_customer_success')

        except Exception as e:
            print("LỖI KHI ĐẶT LỊCH:", e)
            traceback.print_exc()
            messages.error(request, f"Có lỗi xảy ra khi đặt lịch: {e}")

    context = {
        'dich_vu_list': dich_vu_list,
        'locked_dates_json': locked_dates_str,
    }
    return render(request, 'bookings/customer_create.html', context)


@login_required(login_url='/accounts/dang_nhap/')
def booking_customer_list(request):
    trang_thai_filter = request.GET.get('trang_thai', '')
    khach_hang = None

    # Lấy danh sách các ngày đã khóa để truyền ra template chặn lịch
    locked_dates = list(
        NgayHoatDong.objects.filter(trang_thai='Đã khóa')
        .values_list('ngay', flat=True)
    )
    locked_dates_str = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in locked_dates]

    if request.user.is_superuser or request.user.is_staff:
        lich_hen_list = LichHen.objects.select_related('ma_dv', 'ma_kh').exclude(trang_thai='Đã xóa').order_by('-ngay_hen')
    else:
        try:
            tai_khoan_Obj = TaiKhoan.objects.get(user=request.user)
            khach_hang = KhachHang.objects.filter(ma_tk=tai_khoan_Obj).first()
            lich_hen_list = LichHen.objects.select_related('ma_dv', 'ma_kh').filter(ma_kh__ma_tk=tai_khoan_Obj).exclude(trang_thai='Đã xóa').order_by('-ngay_hen')
        except TaiKhoan.DoesNotExist:
            lich_hen_list = LichHen.objects.none()

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
        'locked_dates_json': locked_dates_str,  # <-- Bổ sung dòng này vào context
        **get_staff_context(request)
    })


@login_required(login_url='/accounts/dang_nhap/')
def booking_customer_detail(request, ma_lh):
    # Banner hồ sơ trong customer_base_pro cần biến khach_hang.
    khach_hang = KhachHang.objects.select_related('ma_tk__user').filter(
        ma_tk__user=request.user
    ).first()

    lich_hen_qs = LichHen.objects.select_related('ma_dv', 'ma_kh__ma_tk__user', 'ma_nv')
    # Khách chỉ được xem lịch hẹn của tài khoản chính mình.
    if not (request.user.is_staff or request.user.is_superuser):
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

@login_required(login_url='/accounts/dang_nhap/')
def booking_customer_success(request):
    last_code = request.session.get('last_booking_code')

    lich_hen = None
    if last_code:
        lich_hen = LichHen.objects.select_related(
            'ma_dv', 'ma_kh'
        ).filter(
            ma_lh=last_code,
            ma_kh__ma_tk__user=request.user
        ).first()

    khach_hang = KhachHang.objects.select_related(
        'ma_tk', 'ma_tv'
    ).filter(
        ma_tk__user=request.user
    ).first()

    return render(request, 'bookings/customer_success.html', {
        'lich_hen': lich_hen,
        'khach_hang': khach_hang,
        **get_staff_context(request)
    })

@login_required(login_url='/accounts/dang_nhap/')
def booking_customer_cancel(request, ma_lh):
    """Đổi trạng thái lịch thành Đã hủy, giữ bản ghi trong database."""
    if request.method != 'POST':
        return redirect('booking_customer_list')

    lich_hen = get_object_or_404(
        LichHen, ma_lh=ma_lh, ma_kh__ma_tk__user=request.user
    )

    if lich_hen.trang_thai in ('Đã hủy', 'Hoàn thành', 'Đã xóa'):
        messages.error(request, 'Lịch hẹn này không thể hủy.')
        return redirect('booking_customer_list')

    ngay_gio_hen = datetime.combine(lich_hen.ngay_hen, lich_hen.gio_hen)
    if timezone.is_naive(ngay_gio_hen):
        ngay_gio_hen = timezone.make_aware(
            ngay_gio_hen, timezone.get_current_timezone()
        )

    if ngay_gio_hen - timezone.now() < timedelta(hours=12):
        messages.error(
            request, 'Không thể hủy! Chỉ được hủy trước giờ hẹn ít nhất 12 tiếng.'
        )
        return redirect('booking_customer_list')

    ly_do = request.POST.get('ly_do_huy', '').strip()
    if ly_do == 'Khác':
        ly_do = request.POST.get('ly_do_khac', '').strip()
    if not ly_do:
        messages.error(request, 'Vui lòng nhập lý do hủy lịch.')
        return redirect('booking_customer_list')

    lich_hen.trang_thai = 'Đã hủy'
    lich_hen.ly_do_huy = ly_do
    lich_hen.save(update_fields=['trang_thai', 'ly_do_huy'])

    messages.success(request, f'Đã hủy lịch #{lich_hen.ma_lh} thành công.')
    return redirect(reverse('booking_customer_list') + '?trang_thai=cancelled')

@login_required(login_url='/accounts/dang_nhap/')
@login_required(login_url='/accounts/dang_nhap/')
def booking_customer_reschedule(request, ma_lh):
    # Quay về đúng giao diện của người đang thực hiện đổi lịch.
    redirect_url = (
        'staff_booking_list'
        if request.user.is_staff or request.user.is_superuser
        else 'booking_customer_list'
    )
    if request.method == "POST":
        lich_hen_qs = LichHen.objects.all()
        if not (request.user.is_staff or request.user.is_superuser):
            lich_hen_qs = lich_hen_qs.filter(ma_kh__ma_tk__user=request.user)
        lich_hen = get_object_or_404(lich_hen_qs, ma_lh=ma_lh)

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

            if time_difference.total_seconds() < 12 * 3600:
                messages.error(request,
                               "Không thể đổi lịch! Chỉ được phép thay đổi lịch hẹn trước ít nhất 12 tiếng so với giờ hẹn.")
                return redirect(redirect_url)
        except Exception as e:
            print("Lỗi check thời gian đổi lịch:", e)

        ngay_hen_moi = request.POST.get('ngay_hen_moi')
        gio_hen_moi = request.POST.get('gio_hen_moi')
        ma_dv_moi = request.POST.get('ma_dv_moi')
        so_luong_moi = request.POST.get('so_luong_khach_moi')
        ghi_chu_moi = request.POST.get('ghi_chu_moi')

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

        if NgayHoatDong.objects.filter(ngay=ngay_str, trang_thai='Đã khóa').exists():
            messages.error(request, 'Ngày mới đã bị khóa. Vui lòng chọn ngày khác.')
            return redirect(redirect_url)

        gio_str = gio_hen_moi if gio_hen_moi else lich_hen.gio_hen

        try:
            so_luong_int = int(so_luong_moi) if so_luong_moi else lich_hen.so_luong_khach
        except (ValueError, TypeError):
            so_luong_int = lich_hen.so_luong_khach

        ten_dv_lower = dich_vu_hien_tai.ten_dich_vu.lower()
        is_shampoo = 'shampoo' in ten_dv_lower
        tong_suc_chua = 6 if is_shampoo else 30

        query = LichHen.objects.filter(ngay_hen=ngay_str).exclude(trang_thai='Đã hủy').exclude(ma_lh=lich_hen.ma_lh)

        gio_clean = gio_str.strip().lower()
        target_hour_str = gio_clean.split(':')[0] if ':' in gio_clean else '12'

        matched_bookings = []
        for b in query:
            db_time = str(b.gio_hen).lower().strip()
            if target_hour_str in db_time or gio_clean in db_time:
                matched_bookings.append(b)
            elif 'noon' in db_time and target_hour_str == '12':
                matched_bookings.append(b)

        dat_roi = 0
        for b in matched_bookings:
            is_b_shampoo = 'shampoo' in str(b.ma_dv.ten_dich_vu).lower()
            if is_shampoo and is_b_shampoo:
                dat_roi += b.so_luong_khach
            elif not is_shampoo and not is_b_shampoo:
                dat_roi += b.so_luong_khach

        con_lai = max(0, tong_suc_chua - dat_roi)

        if so_luong_int > con_lai:
            loai_phong = "phòng gội riêng (6 giường)" if is_shampoo else "hệ thống phòng massage (30 giường)"
            messages.error(request, f"Không thể đổi lịch! Khung giờ này cho {loai_phong} chỉ còn trống {con_lai} chỗ.")
            return redirect(redirect_url)

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


@user_passes_test(is_admin, login_url='/accounts/dang_nhap/')
def manage_activity_days(request):
    today = date.today()
    try:
        month = int(request.GET.get('month', today.month))
        year = int(request.GET.get('year', today.year))
        if month < 1 or month > 12:
            raise ValueError
    except ValueError:
        month = today.month
        year = today.year

    prev_month, prev_year = (12, year - 1) if month == 1 else (month - 1, year)
    next_month, next_year = (1, year + 1) if month == 12 else (month + 1, year)

    ngay_khoa_set = set(
        NgayHoatDong.objects.filter(
            trang_thai='Đã khóa',
            ngay__year=year,
            ngay__month=month
        ).values_list('ngay', flat=True)
    )

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdatescalendar(year, month)

    calendar_matrix = []
    for week in month_days:
        week_row = []
        for day in week:
            is_current_month = (day.month == month)
            is_locked = day in ngay_khoa_set

            ly_do = ""
            if is_locked:
                obj = NgayHoatDong.objects.filter(ngay=day, trang_thai='Đã khóa').first()
                if obj:
                    ly_do = obj.ly_do_khoa

            week_row.append({
                'date': day,
                'day_number': day.day,
                'is_current_month': is_current_month,
                'is_locked': is_locked,
                'ly_do': ly_do
            })
        calendar_matrix.append(week_row)

    ngay_da_khoa = NgayHoatDong.objects.filter(trang_thai='Đã khóa').order_by('ngay')
    form = KhoaNgayForm()

    if request.method == 'POST':
        if 'btn_khoa_ngay' in request.POST:
            form = KhoaNgayForm(request.POST)
            if form.is_valid():
                start_date = form.cleaned_data['ngay_bat_dau']
                end_date = form.cleaned_data['ngay_ket_thuc']
                ly_do = form.cleaned_data['ly_do']
                if ly_do == 'Khác':
                    ly_do = form.cleaned_data['nhap_ly_do']

                delta = end_date - start_date
                for i in range(delta.days + 1):
                    current_date = start_date + timedelta(days=i)
                    ngay_hd, created = NgayHoatDong.objects.get_or_create(
                        ngay=current_date,
                        defaults={
                            'ma_nhd': f"NHD_{current_date.strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}",
                            'trang_thai': 'Đã khóa',
                            'ly_do_khoa': ly_do,
                        }
                    )
                    if not created:
                        ngay_hd.trang_thai = 'Đã khóa'
                        ngay_hd.ly_do_khoa = ly_do
                        ngay_hd.save()

                return redirect('quan_ly_ngay_hoat_dong')

    context = {
        'ngay_da_khoa': ngay_da_khoa,
        'form': form,
        'calendar_matrix': calendar_matrix,
        'current_month_year': f"Tháng {month}, {year}",
        'current_month': month,
        'current_year': year,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        **get_staff_context(request)
    }
    return render(request, 'bookings/admin_activity_day.html', context)


@user_passes_test(is_admin, login_url='/accounts/dang_nhap/')
def unlock_activity_day(request, pk):
    ngay_hd = get_object_or_404(NgayHoatDong, pk=pk)
    ngay_hd.trang_thai = 'Hoạt động'
    ngay_hd.ly_do_khoa = None
    ngay_hd.save()
    return redirect('quan_ly_ngay_hoat_dong')


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
        except:
            pass

    gio_clean = gio.strip().lower()
    tong_suc_chua = 6 if loai_dv == 'shampoo' else 30

    try:
        all_bookings = LichHen.objects.filter(ngay_hen=ngay_str).exclude(trang_thai='Đã hủy')

        matched_bookings = []
        target_hour_str = gio_clean.split(':')[0]

        for b in all_bookings:
            db_time = str(b.gio_hen).lower().strip()
            if target_hour_str in db_time or gio_clean in db_time:
                matched_bookings.append(b)
            elif 'noon' in db_time and target_hour_str == '12':
                matched_bookings.append(b)

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


@staff_member_required(login_url='/accounts/dang_nhap/')
def staff_quan_ly_giuong(request):
    ngay_chon = request.GET.get('ngay', datetime.today().strftime('%Y-%m-%d'))
    khung_gio_list = ['09:00', '10:30', '12:00', '13:30', '15:00', '16:30', '18:00', '19:30', '21:00']
    thong_ke_gio = []

    for gio in khung_gio_list:
        query = LichHen.objects.filter(ngay_hen=ngay_chon).exclude(trang_thai='Đã hủy')
        target_hour_str = gio.split(':')[0]
        matched_bookings = []
        for b in query:
            db_time = str(b.gio_hen).lower().strip()
            if target_hour_str in db_time or gio.lower() in db_time:
                matched_bookings.append(b)
            elif 'noon' in db_time and target_hour_str == '12':
                matched_bookings.append(b)

        shampoo_dat = 0
        massage_dat = 0
        for b in matched_bookings:
            if 'shampoo' in str(b.ma_dv.ten_dich_vu).lower():
                shampoo_dat += b.so_luong_khach
            else:
                massage_dat += b.so_luong_khach

        thong_ke_gio.append({
            'gio': gio,
            'shampoo_dat': shampoo_dat,
            'shampoo_trong': max(0, 6 - shampoo_dat),
            'massage_dat': massage_dat,
            'massage_trong': max(0, 30 - massage_dat),
        })

    return render(request, 'bookings/staff_quan_ly_giuong.html', {
        'ngay_chon': ngay_chon,
        'thong_ke_gio': thong_ke_gio,
        **get_staff_context(request)
    })


@staff_member_required(login_url='/accounts/dang_nhap/')
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
            dich_vu = DichVu.objects.filter(pk=ma_dv).first()
            if not dich_vu:
                dich_vu = DichVu.objects.first()
            if not dich_vu:
                messages.error(request, "Lỗi tạo lịch: Không tìm thấy dịch vụ nào trong hệ thống.")
                return redirect('staff_booking_create')

            date_obj = datetime.strptime(ngay_hen.strip(), '%d/%m/%Y').date()
            ngay_check = date_obj.strftime('%Y-%m-%d')

            if ngay_check in locked_dates_str:
                messages.error(request, "Ngày bạn chọn hiện đang đóng cửa (Nghỉ lễ/Bảo trì).")
                return redirect('staff_booking_create')

            # Không tìm khách bằng họ tên: một tên có thể thuộc nhiều hồ sơ.
            if ma_kh_chon:
                khach_hang = KhachHang.objects.filter(pk=ma_kh_chon).first()
                if khach_hang is None:
                    messages.error(request, 'Khách hàng đã chọn không còn tồn tại. Vui lòng chọn lại.')
                    return redirect('staff_booking_create')
                so_khach = getattr(getattr(khach_hang, 'ma_tk', None), 'so_dien_thoai', '')
                if so_khach and sdt != so_khach:
                    messages.error(request, 'Số điện thoại không khớp khách hàng đã chọn. Vui lòng chọn lại.')
                    return redirect('staff_booking_create')
            else:
                if not sdt:
                    messages.error(request, 'Vui lòng chọn khách hàng hoặc nhập số điện thoại.')
                    return redirect('staff_booking_create')
                khach_hang = KhachHang.objects.filter(ma_tk__so_dien_thoai=sdt).first()
                if khach_hang is None:
                    messages.error(request, 'Không tìm thấy tài khoản khách hàng với số điện thoại này. Vui lòng tạo hồ sơ khách hàng trước khi đặt lịch.')
                    return redirect('staff_booking_create')

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
            return redirect('staff_booking_list')

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


@staff_member_required(login_url='/accounts/dang_nhap/')
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

@staff_member_required(login_url='/accounts/dang_nhap/')
def booking_staff_detail(request, ma_lh):
    lich_hen = get_object_or_404(LichHen.objects.select_related('ma_dv', 'ma_kh', 'ma_nv'), ma_lh=ma_lh)
    dich_vu_list = DichVu.objects.all()
    danh_sach_nhan_vien = NhanVien.objects.all()

    return render(request, 'bookings/staff_detail.html', {
        'lich_hen': lich_hen,
        'dich_vu_list': dich_vu_list,
        'danh_sach_nhan_vien': danh_sach_nhan_vien,
        **get_staff_context(request)
    })


@staff_member_required(login_url='/accounts/dang_nhap/')
def booking_staff_complete(request, ma_lh):
    if request.method == "POST":
        lich_hen = get_object_or_404(LichHen, ma_lh=ma_lh)
        lich_hen.trang_thai = 'Hoàn thành'
        lich_hen.save()
        messages.success(request, f"Đã cập nhật lịch hẹn #{lich_hen.ma_lh} thành Hoàn thành thành công!")
    return redirect('staff_booking_detail', ma_lh=ma_lh)


@user_passes_test(is_admin, login_url='/accounts/dang_nhap/')
def booking_admin_delete(request, ma_lh):
    if request.method == "POST":
        lich_hen = get_object_or_404(LichHen, ma_lh=ma_lh)
        ma_hien_tai = lich_hen.ma_lh
        lich_hen.trang_thai = 'Đã xóa'
        lich_hen.ly_do_huy = "Quản trị viên xóa lịch khỏi hệ thống"
        lich_hen.save()
        messages.success(request, f"Đã chuyển lịch hẹn #{ma_hien_tai} sang trạng thái Đã xóa thành công.")

    return redirect('staff_booking_list')


@user_passes_test(is_admin, login_url='/accounts/dang_nhap/')
def assign_staff_to_booking(request, ma_lh):
    lich_hen = get_object_or_404(LichHen, ma_lh=ma_lh)

    if request.method == "POST":
        nhan_vien_id = request.POST.get('nhan_vien_id')
        if nhan_vien_id:
            nhan_vien = get_object_or_404(NhanVien, pk=nhan_vien_id)
            trung_lich = LichHen.objects.filter(
                ngay_hen=lich_hen.ngay_hen,
                gio_hen=lich_hen.gio_hen,
                ma_nv=nhan_vien
            ).exclude(ma_lh=lich_hen.ma_lh).exclude(trang_thai__in=['Đã hủy', 'Đã xóa']).exists()

            if trung_lich:
                messages.error(request,
                               f"Không thể phân công! Nhân viên {nhan_vien.ho_ten} đã có lịch làm việc vào lúc {lich_hen.gio_hen} ngày {lich_hen.ngay_hen} rồi.")
                return redirect('staff_booking_detail', ma_lh=lich_hen.ma_lh)

            lich_hen.ma_nv = nhan_vien
            lich_hen.save()
            messages.success(request,
                             f"Đã phân công nhân viên {nhan_vien.ho_ten} phụ trách lịch hẹn #{ma_lh} thành công!")
        else:
            lich_hen.ma_nv = None
            lich_hen.save()
            messages.success(request, f"Đã hủy phân công nhân viên cho lịch hẹn #{ma_lh}.")

    return redirect('staff_booking_detail', ma_lh=ma_lh)


@staff_member_required(login_url='/accounts/dang_nhap/')
def staff_home(request):
    return render(request, 'core/staff_home.html', get_staff_context(request))
