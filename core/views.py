from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from customers.models import KhachHang
from services.models import DichVu
from django.core.paginator import Paginator



# Trang chủ khách hàng
def customer_home(request):
    return render(request, 'core/customer_home.html')


# Trang chủ nhân viên
def staff_home(request):
    return render(request, 'core/staff_home.html')


# Trang chủ Charm Spa Grand (AMy)
def home(request):
    return render(request, "core/home.html")


# Trang liệu trình (main)
def lieu_trinh_page(request):
    dich_vu_list = list(DichVu.objects.all().order_by('pk'))

    # Sử dụng bộ ảnh dịch vụ hiện có của dự án.
    cards = [
        {
            'service': dv,
            'image': f'images/services/service{(i % 10) + 1}.jpg',
        }
        for i, dv in enumerate(dich_vu_list)
    ]

    page_obj = Paginator(cards, 9).get_page(request.GET.get('page'))

    return render(request, 'core/lieu_trinh.html', {
        'page_obj': page_obj
    })


# Trang hồ sơ khách hàng (main)
@login_required(login_url='/accounts/dang_nhap/')
def customer_profile_view(request):
    # Chỉ lấy hồ sơ thuộc tài khoản đang đăng nhập.
    khach_hang = KhachHang.objects.select_related(
        'ma_tk', 'ma_tv'
    ).filter(
        ma_tk__user=request.user
    ).first()

    return render(request, 'customer/customer_profile.html', {
        'khach_hang': khach_hang
    })


# Trang liên hệ (main)
def contact_view(request):
    if request.method == 'POST':
        ho_ten = request.POST.get('ho_ten', '').strip()
        so_dien_thoai = request.POST.get('so_dien_thoai', '').strip()
        email = request.POST.get('email', '').strip()
        chu_de = request.POST.get('chu_de', '').strip()
        noi_dung = request.POST.get('noi_dung', '').strip()

        # TODO: Lưu yêu cầu liên hệ vào database hoặc gửi email.
        # Hiện tại chưa có bước lưu hoặc gửi thật.

        messages.info(
            request,
            "Thông tin liên hệ đã được tiếp nhận trên biểu mẫu. "
            "Chức năng gửi yêu cầu đến bộ phận hỗ trợ đang được hoàn thiện."
        )
        return redirect('core:contact')

    return render(request, 'core/contact.html')


from django.shortcuts import render


def khong_gian_view(request):
    danh_sach_khong_gian = [
        {"ten": "Khu Vực Trị Liệu", "hinh_anh": "images/khong_gian/khu_vuc_tri_lieu.jpg"},
        {"ten": "Lễ Tân", "hinh_anh": "images/khong_gian/le_tan.jpg"},
        {"ten": "Ngâm Chân Thảo Dược", "hinh_anh": "images/khong_gian/ngam_chan_thao_duoc.jpg"},
        {"ten": "Nhà Hàng", "hinh_anh": "images/khong_gian/nha_hang.jpg"},
        {"ten": "Phòng Gia Đình", "hinh_anh": "images/khong_gian/phong_gia_dinh.jpg"},
        {"ten": "Phòng Massage", "hinh_anh": "images/khong_gian/phong_massage.jpg"},
        {"ten": "Phòng VIP", "hinh_anh": "images/khong_gian/phong_vip.jpg"},
    ]

    context = {
        'khong_gian_list': danh_sach_khong_gian
    }
    return render(request, 'core/khong_gian.html', context)