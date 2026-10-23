from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from customers.models import KhachHang  # (Thay đổi đường dẫn import theo đúng app của bạn)



def customer_profile_view(request):
    try:
        # Lấy thông tin khách hàng dựa vào tài khoản đang đăng nhập hiện tại
        # Giả sử trong model KhachHang có trường liên kết OneToOne hoặc ForeignKey tên là 'ma_tk' hoặc 'user'
        tai_khoan_hien_tai = request.user.thong_tin_tai_khoan
        khach_hang = KhachHang.objects.get(ma_tk=tai_khoan_hien_tai)

        # Bạn cũng có thể truy vấn thêm lịch sử dịch vụ gần đây của khách hàng này nếu cần
        # lich_su_dich_vu = khach_hang.lich_su_dat_lich.all()[:4]

    except (AttributeError, KhachHang.DoesNotExist):
        khach_hang = None
        # lich_su_dich_vu = []

    context = {
        'khach_hang': khach_hang,
        # 'lich_su_dich_vu': lich_su_dich_vu,
    }

    return render(request, 'customer/customer_profile.html', context)