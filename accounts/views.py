from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from .models import TaiKhoan
from .forms import DangKyForm


def dang_ky_view(request):
    if request.method == 'POST':
        form = DangKyForm(request.POST)
        if form.is_valid():
            form.save()  # Lưu user và tự động tạo profile, gán vai trò Khách hàng
            return redirect('dang_nhap')
    else:
        form = DangKyForm()
    return render(request, 'accounts/dang_ky.html', {'form': form})


def dang_nhap_view(request):
    # Nếu user đã đăng nhập rồi thì không cho hiện trang login nữa, tự động điều hướng luôn
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('/home/staff/')
        elif request.user.is_staff:
            return redirect('/home/staff/')
        else:
            return redirect('/home/customer/')

    if request.method == 'POST':
        # Lấy dữ liệu từ form HTML gửi lên (Hỗ trợ nhập Username, Email hoặc Số điện thoại)
        login_input = request.POST.get('username')
        password_nhap = request.POST.get('password')

        user_obj = None

        # =========================================================================
        # <--- THAY ĐỔI: TÌM USER TRƯỚC KHI GỌI authenticate() ĐỂ CHECK is_active TRƯỚC --->
        # =========================================================================
        try:
            user_obj = User.objects.get(username=login_input)
        except User.DoesNotExist:
            if '@' in login_input:
                try:
                    user_obj = User.objects.get(email=login_input)
                except User.DoesNotExist:
                    user_obj = None
            else:
                try:
                    tai_khoan = TaiKhoan.objects.get(so_dien_thoai=login_input)
                    user_obj = tai_khoan.user
                except TaiKhoan.DoesNotExist:
                    user_obj = None

        # Nếu tìm thấy user, kiểm tra khóa tài khoản TRƯỚC
        if user_obj is not None:
            # <--- ĐOẠN KIỂM TRA BỊ KHÓA ĐƯỢC ĐẶT LÊN TRÊN HẾT --->
            if not user_obj.is_active:
                return render(request, 'accounts/dang_nhap.html', {
                    'error': 'Tài khoản của bạn đã bị khóa. Vui lòng liên hệ bộ phận hỗ trợ!'
                })

            # Sau khi check khóa xong mới tiến hành xác thực mật khẩu
            user = authenticate(request, username=user_obj.username, password=password_nhap)

            if user is not None:
                auth_login(request, user)  # Tạo phiên đăng nhập (session)

                # 3. Phân quyền trực tiếp dựa trên cờ chuẩn của Django
                if user.is_superuser:
                    return redirect('/home/staff/')
                elif user.is_staff:
                    return redirect('/home/staff/')
                else:
                    return redirect('/home/customer/')

        # <--- KẾT THÚC ĐOẠN THAY ĐỔI --->

        # Nếu sai thông tin hoặc không tìm thấy user
        return render(request, 'accounts/dang_nhap.html',
                      {'error': 'Tên đăng nhập, số điện thoại hoặc mật khẩu không chính xác!'})

    return render(request, 'accounts/dang_nhap.html')


def dang_xuat_view(request):
    auth_logout(request)
    return redirect('dang_nhap')

