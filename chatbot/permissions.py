from functools import wraps

from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect

from . import identity


def _wants_json(request):
    return (request.headers.get('x-requested-with') == 'XMLHttpRequest'
            or 'application/json' in request.headers.get('accept', '')
            or request.content_type == 'application/json')


def admin_required(view):
    """Chỉ Quản trị viên (vai_tro = 'Quản trị viên' hoặc superuser)."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if _wants_json(request):
                return JsonResponse({'ok': False, 'error': 'Phiên đăng nhập đã hết hạn.'}, status=401)
            return redirect('dang_nhap')
        if not identity.is_admin(request.user):
            if _wants_json(request):
                return JsonResponse({'ok': False, 'error': 'Chỉ quản trị viên được thực hiện thao tác này.'}, status=403)
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper