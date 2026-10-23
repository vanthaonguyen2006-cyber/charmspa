from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password
from .forms import DangKyForm
from .models import TaiKhoan

def dang_ky_view(request):
    if request.method == 'POST':
        form = DangKyForm(request.POST)
        if form.is_valid():
            # Lấy dữ liệu từ form nhưng chưa lưu vội vào database
            tai_khoan = form.save(commit=False)

            # Tự động sinh mã tài khoản tăng dần (TK001, TK002...)
            count_tk = TaiKhoan.objects.count() + 1
            tai_khoan.ma_tk = f"TK{count_tk:03d}"

            # Lấy mật khẩu thô, tiến hành băm (hash) bảo mật rồi gán vào database
            mat_khau_tho = form.cleaned_data.get('mat_khau')
            tai_khoan.mat_khau = make_password(mat_khau_tho)

            # Gán vai trò là Khách hàng và trạng thái Hoạt động
            tai_khoan.vai_tro = 'Khách hàng'
            tai_khoan.trang_thai = 'Hoạt động'

            # Lưu xuống cơ sở dữ liệu SQLite
            tai_khoan.save()

            return redirect('dang_nhap')
    else:
        form = DangKyForm()

    return render(request, 'accounts/dang_ky.html', {'form': form})


from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password
from .forms import DangNhapForm  # Import form vừa tạo
from .models import TaiKhoan

from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password
from .forms import DangNhapForm
from .models import TaiKhoan


def dang_nhap_view(request):
    if request.method == 'POST':
        form = DangNhapForm(request.POST)
        if form.is_valid():
            username_nhap = form.cleaned_data.get('username')
            mat_khau_nhap = form.cleaned_data.get('mat_khau')

            try:
                tai_khoan = TaiKhoan.objects.get(username=username_nhap)

                if check_password(mat_khau_nhap, tai_khoan.mat_khau):
                    # Lưu thông tin vào session
                    request.session['ma_tk'] = tai_khoan.ma_tk
                    request.session['username'] = tai_khoan.username
                    request.session['vai_tro'] = tai_khoan.vai_tro

                    # KIỂM TRA VAI TRÒ VÀ ĐIỀU HƯỚNG TRANG PHÙ HỢP
                    if tai_khoan.vai_tro == 'Khách hàng':
                        # Thay 'customer_home' (hoặc tên đường dẫn trang khách hàng của bạn) vào đây
                        return redirect('customer_home')
                    else:
                        return redirect('/')  # Hoặc chuyển về trang quản trị nếu là nhân viên/admin
                else:
                    form.add_error(None, "Mật khẩu không chính xác!")
            except TaiKhoan.DoesNotExist:
                form.add_error(None, "Tên đăng nhập không tồn tại!")
    else:
        form = DangNhapForm()

    return render(request, 'accounts/dang_nhap.html', {'form': form})


def dang_xuat_view(request):
    request.session.flush() # Xóa toàn bộ session
    return redirect('/')