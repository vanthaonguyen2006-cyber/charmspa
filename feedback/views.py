from django.shortcuts import render, redirect
from django.contrib import messages
from customers.models import KhachHang
from .forms import PhanHoiKhieuNaiForm
from .models import PhanHoiKhieuNai


def gui_phan_hoi(request):
    # Tạm dùng khách hàng test trong giai đoạn code riêng module
    khach_hang = KhachHang.objects.first()

    if not khach_hang:
        messages.error(request, 'Chưa có dữ liệu khách hàng để thử nghiệm.')
        return render(request, 'feedback/gui_phan_hoi.html', {
            'form': PhanHoiKhieuNaiForm()
        })

    if request.method == 'POST':
        form = PhanHoiKhieuNaiForm(request.POST)

        if form.is_valid():
            phan_hoi = form.save(commit=False)
            phan_hoi.ma_kh = khach_hang

            so_luong = PhanHoiKhieuNai.objects.count() + 1
            phan_hoi.ma_ph = f'PH{so_luong:03d}'

            phan_hoi.save()

            messages.success(
                request,
                'Gửi phản hồi/khiếu nại thành công.'
            )

            return redirect('feedback:gui_phan_hoi')

    else:
        form = PhanHoiKhieuNaiForm()

    return render(request, 'feedback/gui_phan_hoi.html', {
        'form': form,
        'khach_hang': khach_hang
    })




#test base giao diện chung
def test_staff(request):
    return render(request, 'feedback/test_staff.html')