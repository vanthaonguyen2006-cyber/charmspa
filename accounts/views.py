from django.shortcuts import render, redirect
from .forms import DangKyForm

def dang_ky_view(request):
    if request.method == 'POST':
        form = DangKyForm(request.POST)
        if form.is_valid():
            form.save() # Hệ thống tự lo việc băm pass, tạo user và tạo profile liên kết chuẩn
            return redirect('dang_nhap')
    else:
        form = DangKyForm()
    return render(request, 'accounts/dang_ky.html', {'form': form})


from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from .models import TaiKhoan


from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from .models import TaiKhoan

def dang_nhap_view(request):
    if request.method == 'POST':
        # Lấy dữ liệu từ form HTML gửi lên (name="username" và name="password")
        login_input = request.POST.get('username')  # Có thể là username, email hoặc số điện thoại
        password_nhap = request.POST.get('password')

        user = None

        # 1. Kiểm tra xem người dùng nhập vào là Username, Email hay Số điện thoại
        if '@' in login_input:
            # Nếu nhập email
            try:
                user_obj = User.objects.get(email=login_input)
                username_thuc = user_obj.username
                user = authenticate(request, username=username_thuc, password=password_nhap)
            except User.DoesNotExist:
                user = None
        else:
            # Kiểm tra xem có khớp với số điện thoại trong bảng TaiKhoan không
            try:
                tai_khoan = TaiKhoan.objects.get(so_dien_thoai=login_input)
                username_thuc = tai_khoan.user.username
                user = authenticate(request, username=username_thuc, password=password_nhap)
            except TaiKhoan.DoesNotExist:
                # Nếu không phải SĐT thì thử coi như nhập trực tiếp Username
                user = authenticate(request, username=login_input, password=password_nhap)

        # 2. Nếu xác thực thành công
        if user is not None:
            auth_login(request, user)  # Tạo phiên đăng nhập (session)

            # Lấy và lưu vai trò vào session để tiện phân quyền
            try:
                role = user.thong_tin_tai_khoan.vai_tro
                request.session['vai_tro'] = role
            except Exception:
                role = 'Khách hàng'
                request.session['vai_tro'] = role

            # 3. ĐIỀU HƯỚNG LINH HOẠT THEO TỪNG VAI TRÒ
            if role == "Quản trị viên":
                return redirect('/admin/')
            elif role == "Nhân viên":
                return redirect('/staff/dashboard/')  # Thay đổi đường dẫn trang của nhân viên nếu cần
            else:
                return redirect('/home/customer/')    # Dành cho Khách hàng
        else:
            # Nếu sai thông tin, truyền báo lỗi ra giao diện
            return render(request, 'accounts/dang_nhap.html',
                          {'error': 'Thông tin đăng nhập hoặc mật khẩu không chính xác!'})

    return render(request, 'accounts/dang_nhap.html')

from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect

def dang_xuat_view(request):
    auth_logout(request)
    return redirect('dang_nhap')
