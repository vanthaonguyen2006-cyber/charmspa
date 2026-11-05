from django.db.models import Q
from .models import ThongBaoKhachHang

def user_notifications(request):
    """
    Context Processor trả về thông báo và số lượng chưa đọc.
    Đã được bọc kiểm tra an toàn 100% cho Admin, Staff và Khách hàng.
    """
    empty_context = {
        'user_notifications': [],
        'notifications': [],
        'unread_count': 0
    }

    # 1. Bỏ qua nếu là request trong trang Admin
    path = getattr(request, 'path', '')
    if path.startswith('/admin'):
        return empty_context

    # 2. Bỏ qua nếu user chưa đăng nhập
    user = getattr(request, 'user', None)
    if not user or not getattr(user, 'is_authenticated', False):
        return empty_context

    # 3. Lấy dữ liệu thông báo an toàn
    try:
        notifications_qs = ThongBaoKhachHang.objects.filter(
            Q(ma_kh=user) |
            Q(ma_kh__user=user) |
            Q(ma_kh__ma_tk=user)
        ).order_by('-thoi_gian_gui')

        unread_count = notifications_qs.filter(
            Q(trang_thai_gui='Chưa đọc') | Q(trang_thai_gui='Chưa gửi')
        ).count()

        recent_notifications = list(notifications_qs[:5])

        return {
            'user_notifications': recent_notifications,
            'notifications': recent_notifications,
            'unread_count': unread_count
        }

    except Exception:
        return empty_context