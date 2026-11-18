from functools import wraps
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect

from accounts.models import is_customer_role
from . import identity


def _wants_json(request):
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('accept', '')
        or (request.content_type and 'application/json' in request.content_type)
    )


def role_passes_test(test_func, login_url='dang_nhap', error_msg='Bạn không có quyền thực hiện thao tác này.'):
    """Decorator dùng user_passes_test kết hợp trả lỗi JSON 401/403 cho các request AJAX."""
    def decorator(view_func):
        django_test = user_passes_test(test_func, login_url=login_url)

        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if _wants_json(request):
                    return JsonResponse({'ok': False, 'error': 'Phiên đăng nhập đã hết hạn.'}, status=401)
                return redirect(login_url)

            if not test_func(request.user):
                if _wants_json(request):
                    return JsonResponse({'ok': False, 'error': error_msg}, status=403)
                raise PermissionDenied(error_msg)

            return django_test(view_func)(request, *args, **kwargs)

        return _wrapped_view
    return decorator


# 1. Quyền Quản lý kịch bản Chatbot: Chỉ Quản lý (is_manager_role) hoặc Superuser
admin_required = role_passes_test(
    identity.is_admin,
    error_msg='Chỉ vai trò Quản lý hoặc Superuser mới có quyền chỉnh sửa kịch bản Chatbot.'
)

# 2. Quyền Quản lý hội thoại: Nhân viên, Quản lý (is_staff_portal_user) hoặc Superuser
staff_portal_required = role_passes_test(
    identity.is_staff_user,
    error_msg='Chỉ Nhân viên, Quản lý hoặc Superuser mới được truy cập trang Quản lý hội thoại.'
)

# 3. Quyền Khách hàng
customer_required = role_passes_test(
    is_customer_role,
    error_msg='Trang này chỉ dành cho tài khoản Khách hàng.'
)