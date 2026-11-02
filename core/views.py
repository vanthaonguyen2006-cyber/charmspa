from django.shortcuts import render
from customers.models import KhachHang
from services.models import DichVu
from django.core.paginator import Paginator

def customer_home(request):
    return render(request, 'core/customer_home.html')

def staff_home(request):
    return render(request, 'core/staff_home.html')

def lieu_trinh_page(request):
    dich_vu_list = list(DichVu.objects.all().order_by('pk'))
    # Dùng bộ ảnh dịch vụ hiện có của dự án: service1.jpg ... service10.jpg.
    # Ảnh 11+ tạm dùng lại ảnh trong bộ 10; thay đường dẫn khi có ảnh riêng.
    cards = [
        {
            'service': dv,
            'image': f'images/services/service{(i % 10) + 1}.jpg',
        }
        for i, dv in enumerate(dich_vu_list)
    ]
    page_obj = Paginator(cards, 9).get_page(request.GET.get('page'))
    return render(request, 'core/lieu_trinh.html', {'page_obj': page_obj})