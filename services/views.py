"""Charm Spa service management views.

Replace services/views.py only after backing it up. Requires wiring the delete route
in services/urls.py (or the project's corresponding URLConf).
"""
import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from accounts.models import is_customer_role, is_manager_role, is_staff_portal_user
from customers.models import KhachHang
from services.models import DichVu, DichVuDaSuDung

logger = logging.getLogger(__name__)
LOGIN_URL = '/accounts/dang_nhap/'


def role_required(check_role, *, api=False):
    """Enforce business roles from TaiKhoan.vai_tro (not Django is_staff).

    Authentication is handled by the outer @login_required decorator.
    Authenticated users without access receive 403 instead of a login redirect.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not check_role(request.user):
                if api:
                    return JsonResponse(
                        {'success': False, 'error': 'Bạn không có quyền thực hiện thao tác này.'},
                        status=403,
                    )
                return HttpResponseForbidden('Bạn không có quyền truy cập trang này.')
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def _parse_service_data(post, existing=None):
    """Validate the actual fields in services.DichVu, without altering promo data."""
    name = post.get('ten_dich_vu', '').strip()
    category = post.get('loai_dich_vu', '').strip()
    description = post.get('mo_ta', existing.mo_ta or '' if existing else '').strip()
    if not name or len(name) > 100:
        raise ValueError('Tên dịch vụ phải có từ 1 đến 100 ký tự.')
    if not category or len(category) > 50:
        raise ValueError('Loại dịch vụ phải có từ 1 đến 50 ký tự.')
    try:
        duration = int(post.get('thoi_luong', ''))
        capacity = int(post.get('suc_chua_toi_da', str(existing.suc_chua_toi_da) if existing else '30') or '30')
        points = int(post.get('diem_tich_luy', post.get('diem_tich_luy_dich_vu', '')))
        price = Decimal(str(post.get('gia_dich_vu', '')).strip())
    except (ValueError, TypeError, InvalidOperation):
        raise ValueError('Thời lượng, sức chứa, giá và điểm phải là số hợp lệ.')
    if duration <= 0:
        raise ValueError('Thời lượng phải lớn hơn 0 phút.')
    if capacity <= 0:
        raise ValueError('Sức chứa tối đa phải lớn hơn 0.')
    if points < 0:
        raise ValueError('Điểm tích lũy không được âm.')
    if not price.is_finite() or price <= 0 or price > Decimal('9999999999.99'):
        raise ValueError('Giá dịch vụ phải lớn hơn 0 và nằm trong giới hạn cho phép.')
    if price.as_tuple().exponent < -2:
        raise ValueError('Giá dịch vụ chỉ được có tối đa 2 chữ số thập phân.')
    return {
        'ten_dich_vu': name,
        'loai_dich_vu': category,
        'mo_ta': description,
        'thoi_luong': duration,
        'suc_chua_toi_da': capacity,
        'gia_dich_vu': price,
        'diem_tich_luy_dich_vu': points,
    }


def _service_payload(item):
    return {
        'ma_dv': item.ma_dv,
        'ten_dich_vu': item.ten_dich_vu,
        'loai_dich_vu': item.loai_dich_vu,
        'mo_ta': item.mo_ta or '',
        'thoi_luong': item.thoi_luong,
        'suc_chua_toi_da': item.suc_chua_toi_da,
        'gia_dich_vu': str(item.gia_dich_vu),
        'gia_formatted': f'{item.gia_dich_vu:,.0f} đ'.replace(',', '.'),
        'diem_tich_luy': item.diem_tich_luy_dich_vu,
        # DichVu has no trang_thai field. Do not pretend this controls booking availability.
        'trang_thai': True,
    }


@login_required(login_url=LOGIN_URL)
@role_required(is_staff_portal_user)
def staff_services(request):
    queryset = DichVu.objects.all().order_by('ma_dv')
    services = [_service_payload(item) for item in queryset]
    context = {
        'today': date.today(),
        'services': services,
        'active_menu': 'dich_vu',
        'can_manage_services': is_manager_role(request.user),
        'tong_dich_vu': len(services),
        'so_loai_dich_vu': len({row['loai_dich_vu'] for row in services}),
    }
    return render(request, 'services/staff_service_list.html', context)


@login_required(login_url=LOGIN_URL)
@role_required(is_manager_role, api=True)
@require_POST
def api_them_dich_vu(request):
    try:
        fields = _parse_service_data(request.POST)
    except ValueError as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)
    try:
        with transaction.atomic():
            existing = list(DichVu.objects.values_list('ma_dv', flat=True))
            numbers = [int(code[2:]) for code in existing if re.fullmatch(r'DV\d+', code or '')]
            next_number = max(numbers, default=0) + 1
            code = f'DV{next_number:02d}'
            # Conflict detection; database uniqueness protects primary key.
            while code in existing:
                next_number += 1
                code = f'DV{next_number:02d}'
            service = DichVu.objects.create(ma_dv=code, **fields)
        return JsonResponse({'success': True, 'message': 'Thêm dịch vụ thành công!', 'service': _service_payload(service)})
    except IntegrityError:
        return JsonResponse({'success': False, 'error': 'Mã dịch vụ vừa được tạo bởi yêu cầu khác. Vui lòng thử lại.'}, status=409)
    except Exception:
        logger.exception('Service create failed')
        return JsonResponse({'success': False, 'error': 'Không thể thêm dịch vụ. Vui lòng thử lại.'}, status=500)


@login_required(login_url=LOGIN_URL)
@role_required(is_manager_role, api=True)
@require_POST
def api_sua_dich_vu(request):
    code = request.POST.get('ma_dv', '').strip()
    if not code:
        return JsonResponse({'success': False, 'error': 'Thiếu mã dịch vụ.'}, status=400)
    try:
        with transaction.atomic():
            service = DichVu.objects.select_for_update().filter(ma_dv=code).first()
            if service is None:
                return JsonResponse({'success': False, 'error': 'Không tìm thấy dịch vụ cần sửa.'}, status=404)
            try:
                fields = _parse_service_data(request.POST, existing=service)
            except ValueError as exc:
                return JsonResponse({'success': False, 'error': str(exc)}, status=400)
            for key, value in fields.items():
                setattr(service, key, value)
            service.save(update_fields=list(fields))
        return JsonResponse({'success': True, 'message': 'Cập nhật dịch vụ thành công!', 'service': _service_payload(service)})
    except Exception:
        logger.exception('Service update failed')
        return JsonResponse({'success': False, 'error': 'Không thể sửa dịch vụ. Vui lòng thử lại.'}, status=500)


@login_required(login_url=LOGIN_URL)
@role_required(is_manager_role, api=True)
@require_POST
def api_xoa_dich_vu(request):
    """Delete only services with zero references in any related model."""
    code = request.POST.get('ma_dv', '').strip()
    if not code:
        return JsonResponse({'success': False, 'error': 'Thiếu mã dịch vụ.'}, status=400)
    try:
        with transaction.atomic():
            service = DichVu.objects.select_for_update().filter(ma_dv=code).first()
            if service is None:
                return JsonResponse({'success': False, 'error': 'Không tìm thấy dịch vụ.'}, status=404)
            # Cover booking, manual history, promotions and any other reverse FK/O2O,
            # including future relations, to avoid cascading deletion of business history.
            for relation in service._meta.related_objects:
                field = relation.field
                if field.many_to_many:
                    continue
                if relation.related_model._default_manager.filter(**{field.name: service}).exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'Dịch vụ đã có Booking, ưu đãi hoặc dữ liệu liên quan nên không được xóa.',
                    }, status=409)
            service.delete()
        return JsonResponse({'success': True, 'message': 'Đã xóa dịch vụ chưa được sử dụng.'})
    except Exception:
        logger.exception('Service delete failed')
        return JsonResponse({'success': False, 'error': 'Không thể xóa dịch vụ do có dữ liệu liên quan hoặc lỗi hệ thống.'}, status=409)


@login_required(login_url=LOGIN_URL)
@role_required(is_customer_role)
def customer_service_history_view(request):
    """Customer-only service history, using the current business role system."""
    tai_khoan = getattr(request.user, 'thong_tin_tai_khoan', None)
    khach_hang = getattr(tai_khoan, 'ho_so_khach_hang', None) if tai_khoan else None
    if not khach_hang:
        khach_hang = (KhachHang.objects.select_related('ma_tk', 'ma_tv')
                      .filter(ma_tk__user=request.user).first())
    lich_su_dich_vu = []
    tong_so_dich_vu = 0
    if khach_hang and hasattr(khach_hang, 'ma_kh'):
        try:
            qs = (DichVuDaSuDung.objects.filter(ma_kh=khach_hang)
                  .select_related('ma_dv', 'ma_nv').order_by('-ngay_su_dung'))
            tong_so_dich_vu = qs.count()
            lich_su_dich_vu = list(qs)
        except Exception:
            logger.exception('Customer service history lookup failed')
    if not khach_hang:
        class TempKhachHang:
            ho_ten = request.user.get_full_name() or request.user.username
            ngay_sinh = None
            gioi_tinh = 'Nam'
            ma_kh = 'Chưa có mã'
            diem_tich_luy_kh = 0
            ma_tv = None

            @property
            def ma_tk(self):
                class DummyTk:
                    so_dien_thoai = tai_khoan.so_dien_thoai if tai_khoan else ''
                return DummyTk()
        khach_hang = TempKhachHang()
    return render(request, 'services/customer_service_history.html', {
        'khach_hang': khach_hang,
        'tai_khoan': tai_khoan,
        'lich_su_dich_vu': lich_su_dich_vu,
        'tong_so_dich_vu': tong_so_dich_vu,
    })
