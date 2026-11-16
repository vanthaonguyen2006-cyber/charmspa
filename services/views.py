from datetime import date
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from bookings.models import DichVu
from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from bookings.models import DichVu
from services.models import DichVuDaSuDung
from customers.models import KhachHang
def is_staff(user):
    return user.is_authenticated and (user.is_staff or getattr(user, 'vai_tro', '') in ['Staff', 'Admin'])


@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
@require_POST
def api_sua_dich_vu(request):
    """
    API xử lý cập nhật thông tin dịch vụ qua AJAX
    """
    try:
        ma_dv = request.POST.get('ma_dv', '').strip()
        ten_dich_vu = request.POST.get('ten_dich_vu', '').strip()
        loai_dich_vu = request.POST.get('loai_dich_vu', '').strip()
        thoi_luong = int(request.POST.get('thoi_luong', 0) or 0)
        gia_dich_vu = float(request.POST.get('gia_dich_vu', 0) or 0)
        diem_tich_luy = int(request.POST.get('diem_tich_luy', 0) or 0)

        if not ma_dv or not ten_dich_vu:
            return JsonResponse({'success': False, 'error': 'Thiếu thông tin mã hoặc tên dịch vụ!'})

        # Tìm dịch vụ trong database theo mã
        service = DichVu.objects.filter(ma_dv=ma_dv).first()
        if not service:
            return JsonResponse({'success': False, 'error': 'Không tìm thấy dịch vụ cần sửa!'})

        # Cập nhật thông tin mới
        service.ten_dich_vu = ten_dich_vu
        service.loai_dich_vu = loai_dich_vu
        service.thoi_luong = thoi_luong
        service.gia_dich_vu = gia_dich_vu
        service.diem_tich_luy_dich_vu = diem_tich_luy
        service.save()

        return JsonResponse({
            'success': True,
            'message': 'Cập nhật dịch vụ thành công!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
def staff_services(request):
    """
    Trang Quản lý dịch vụ dành riêng cho Nhân viên (Staff/Admin)
    """
    services_qs = DichVu.objects.all().order_by('ma_dv')

    services = []
    for item in services_qs:
        # 1. Xử lý mã dịch vụ an toàn tuyệt đối
        ma_dv = getattr(item, 'ma_dv', None)
        if not ma_dv:
            pk_val = getattr(item, 'pk', 1)
            try:
                pk_int = int(pk_val)
            except (ValueError, TypeError):
                pk_int = 1
            ma_dv = f"DV{pk_int:02d}"

        # 2. Xử lý giá dịch vụ an toàn tuyệt đối
        raw_gia = getattr(item, 'gia_dich_vu', 0)
        gia_float = 0.0
        if raw_gia is not None:
            if isinstance(raw_gia, (int, float)):
                gia_float = float(raw_gia)
            else:
                cleaned_str = ''.join(c for c in str(raw_gia) if c.isdigit() or c == '.')
                try:
                    gia_float = float(cleaned_str) if cleaned_str else 0.0
                except ValueError:
                    gia_float = 0.0

        services.append({
            'ma_dv': ma_dv,
            'ten_dich_vu': getattr(item, 'ten_dich_vu', ''),
            'loai_dich_vu': getattr(item, 'loai_dich_vu', ''),
            'thoi_luong': getattr(item, 'thoi_luong', 0),
            'gia_formatted': f"{int(gia_float):,.0f} đ".replace(',', '.'),
            'diem_tich_luy': getattr(item, 'diem_tich_luy_dich_vu', 0),
            'trang_thai': True
        })

    context = {
        'today': date.today(),
        'services': services,
        'active_menu': 'dich_vu'
    }
    return render(request, 'services/staff_service_list.html', context)


@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_staff, login_url='/accounts/dang_nhap/')
@require_POST
def api_them_dich_vu(request):
    """
    API xử lý thêm dịch vụ mới từ Popup Modal
    """
    try:
        ten_dich_vu = request.POST.get('ten_dich_vu', '').strip()
        loai_dich_vu = request.POST.get('loai_dich_vu', '').strip()
        thoi_luong = int(request.POST.get('thoi_luong', 0) or 0)
        gia_dich_vu = float(request.POST.get('gia_dich_vu', 0) or 0)
        diem_tich_luy = int(request.POST.get('diem_tich_luy', 0) or 0)

        if not ten_dich_vu:
            return JsonResponse({'success': False, 'error': 'Tên dịch vụ không được để trống!'})

        # 📌 Tự động sinh mã dịch vụ tiếp theo (VD: DV16 -> tự sinh DV17)
        last_service = DichVu.objects.all().order_by('-ma_dv').first()
        if last_service and last_service.ma_dv and last_service.ma_dv.startswith('DV'):
            try:
                num = int(last_service.ma_dv.replace('DV', ''))
                next_ma_dv = f"DV{num + 1:02d}"
            except ValueError:
                next_ma_dv = f"DV{DichVu.objects.count() + 1:02d}"
        else:
            next_ma_dv = f"DV{DichVu.objects.count() + 1:02d}"

        # Tạo dịch vụ mới trong Database
        new_service = DichVu.objects.create(
            ma_dv=next_ma_dv,
            ten_dich_vu=ten_dich_vu,
            loai_dich_vu=loai_dich_vu,
            thoi_luong=thoi_luong,
            gia_dich_vu=gia_dich_vu,
            diem_tich_luy_dich_vu=diem_tich_luy,
            suc_chua_toi_da=30
        )

        return JsonResponse({
            'success': True,
            'message': 'Thêm dịch vụ thành công!',
            'service': {
                'ma_dv': new_service.ma_dv,
                'ten_dich_vu': new_service.ten_dich_vu,
                'loai_dich_vu': getattr(new_service, 'loai_dich_vu', ''),
                'thoi_luong': new_service.thoi_luong,
                'gia_formatted': f"{int(new_service.gia_dich_vu):,.0f} đ".replace(',', '.'),
                'diem_tich_luy': getattr(new_service, 'diem_tich_luy_dich_vu', 0),
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def is_customer_user(user):
    return user.is_authenticated and not user.is_staff and not user.is_superuser


@login_required(login_url='/accounts/dang_nhap/')
@user_passes_test(is_customer_user, login_url='/home/staff/')
def customer_service_history_view(request):
    """Trang Lịch sử dịch vụ dành cho Khách hàng (thuộc app services)."""
    if request.user.is_staff or request.user.is_superuser:
        return redirect('/home/staff/')

    tai_khoan = getattr(request.user, 'thong_tin_tai_khoan', None)

    khach_hang = None
    if tai_khoan:
        khach_hang = getattr(tai_khoan, 'ho_so_khach_hang', None)
    if not khach_hang:
        khach_hang = (
            KhachHang.objects.select_related('ma_tk', 'ma_tv')
            .filter(ma_tk__user=request.user)
            .first()
        )

    lich_su_dich_vu = []
    tong_so_dich_vu = 0
    if khach_hang and hasattr(khach_hang, 'ma_kh'):
        try:
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
        'tong_so_dich_vu': tong_so_dich_vu,
    }
    return render(request, 'services/customer_service_history.html', context)