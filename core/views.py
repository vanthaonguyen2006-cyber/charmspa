from django.shortcuts import render, redirect
from django.contrib import messages
from customers.models import KhachHang

def customer_home(request):
    return render(request, 'core/customer_home.html')





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


def contact_view(request):
    if request.method == 'POST':
        ho_ten = request.POST.get('ho_ten')
        so_dien_thoai = request.POST.get('so_dien_thoai')
        email = request.POST.get('email')
        chu_de = request.POST.get('chu_de')
        noi_dung = request.POST.get('noi_dung')

        # Xử lý lưu thông tin hoặc gửi Email chăm sóc khách hàng tại đây

        messages.success(request,
                         f"Cảm ơn {ho_ten}! Yêu cầu liên hệ của bạn đã được gửi thành công. Charm Spa Grand sẽ phản hồi trong thời gian sớm nhất.")
        return redirect('core:contact')

    return render(request, 'core/contact.html')
def staff_home(request):
    return render(request, 'core/staff_home.html')
