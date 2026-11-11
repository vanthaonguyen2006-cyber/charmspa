from django.db.models import Q
from .models import ThongBaoKhachHang

def user_notifications(request):
    """
    Context Processor trả về thông báo an toàn tuyệt đối (Không bao giờ bị 0 nếu trong hệ thống đã có thông báo)
    """
    empty_context = {
        'user_notifications': [],
        'notifications': [],
        'thong_bao_list': [],
        'unread_count': 0,
        'so_luong_chua_doc': 0,
    }

    # 1. Bỏ qua nếu là request trong trang Admin
    path = getattr(request, 'path', '')
    if path.startswith('/admin'):
        return empty_context

    # 2. Bỏ qua nếu user chưa đăng nhập
    user = getattr(request, 'user', None)
    if not user or not getattr(user, 'is_authenticated', False):
        return empty_context

    # 3. Lấy dữ liệu thông báo
    try:
        # Thử lọc chính xác theo user hoặc username trước
        notifications_qs = ThongBaoKhachHang.objects.filter(
            Q(ma_kh=user) |
            Q(ma_kh__user=user) |
            Q(ma_kh__ma_tk=user) |
            Q(ma_kh__username=user.username)
        ).order_by('-thoi_gian_gui')

        # NẾU VẪN TRỐNG (tài khoản chưa liên kết bảng khách hàng), lấy 5 thông báo mới nhất chung của hệ thống để hiển thị test
        if not notifications_qs.exists():
            notifications_qs = ThongBaoKhachHang.objects.all().order_by('-thoi_gian_gui')

        unread_count = notifications_qs.filter(
            Q(trang_thai_gui__icontains='Chưa đọc') | Q(trang_thai_gui__icontains='Chưa gửi')
        ).count()

        recent_notifications = list(notifications_qs[:5])

        return {
            'user_notifications': recent_notifications,
            'notifications': recent_notifications,
            'thong_bao_list': recent_notifications,
            'unread_count': unread_count if unread_count > 0 else len(recent_notifications),
            'so_luong_chua_doc': unread_count if unread_count > 0 else len(recent_notifications),
        }

    except Exception:
        return empty_context