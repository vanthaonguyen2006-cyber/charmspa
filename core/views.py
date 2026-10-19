from django.shortcuts import render

def customer_home(request):
    return render(request, 'core/customer_home.html')


from django.shortcuts import render
from customers.models import KhachHang


def customer_profile_view(request):
    # Lấy thông tin khách hàng dựa trên tài khoản đang đăng nhập
    # (Ví dụ dựa vào email hoặc session ma_tk của bạn)
    try:
        # Nếu bạn lưu email trong session hoặc request.user:
        # khach_hang = KhachHang.objects.get(email=request.user.email)

        # Tạm thời lấy khách hàng đầu tiên (hoặc theo session/request của bạn):
        khach_hang = KhachHang.objects.select_related('ma_tk', 'ma_tv').first()
    except KhachHang.DoesNotExist:
        khach_hang = None

    context = {
        'khach_hang': khach_hang,
    }
    return render(request, 'customer/customer_profile.html', context)