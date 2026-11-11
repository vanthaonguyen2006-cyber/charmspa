from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import TaiKhoan
from .forms import DangKyForm, AccountPasswordChangeForm


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
        if request.user.is_superuser or request.user.is_staff:
            return redirect('/home/staff/dashboard/')
        else:
            return redirect('/home/')

    if request.method == 'POST':
        # Lấy dữ liệu từ form HTML gửi lên (Hỗ trợ nhập Username, Email hoặc Số điện thoại)
        login_input = request.POST.get('username', '').strip()
        password_nhap = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me')

        user_obj = None

        # 1. Tìm user theo Username, Email hoặc Số điện thoại
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

        # 2. Nếu tìm thấy user, kiểm tra trạng thái khóa TRƯỚC
        if user_obj is not None:
            if not user_obj.is_active:
                return render(request, 'accounts/dang_nhap.html', {
                    'error': 'Tài khoản của bạn đã bị khóa. Vui lòng liên hệ bộ phận hỗ trợ!',
                    'login_input': login_input,
                    'remember_me': bool(remember_me),
                })

            # Xác thực mật khẩu
            user = authenticate(request, username=user_obj.username, password=password_nhap)

            if user is not None:
                auth_login(request, user)  # Tạo phiên đăng nhập

                # --- XỬ LÝ GHI NHỚ ĐĂNG NHẬP ---
                if remember_me:
                    # Tích chọn: Duy trì phiên đăng nhập trong 14 ngày (14 * 24 * 60 * 60 = 1,209,600 giây)
                    request.session.set_expiry(1209600)
                else:
                    # Không tích chọn: Phiên đăng nhập sẽ hết hạn ngay khi đóng trình duyệt
                    request.session.set_expiry(0)

                # Phân quyền chuyển hướng
                if user.is_superuser or user.is_staff:
                    return redirect('/home/staff/dashboard/')
                else:
                    return redirect('/home/')

        # 3. Nếu sai thông tin hoặc mật khẩu không đúng (Thất bại: giữ lại login_input và remember_me)
        return render(request, 'accounts/dang_nhap.html', {
            'error': 'Tên đăng nhập, số điện thoại hoặc mật khẩu không chính xác!',
            'login_input': login_input,
            'remember_me': bool(remember_me),
        })

    return render(request, 'accounts/dang_nhap.html')


def dang_xuat_view(request):
    """Đăng xuất tài khoản, xóa phiên và làm sạch session hoàn toàn"""
    auth_logout(request)
    return redirect('dang_nhap')

@login_required(login_url='/accounts/dang_nhap/')
def account_change_password_view(request):
    """Change the password for a signed-in customer account."""
    if request.user.is_staff or request.user.is_superuser:
        return redirect('/home/staff/')

    form = AccountPasswordChangeForm(
        user=request.user,
        data=request.POST if request.method == 'POST' else None,
    )

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Mật khẩu của bạn đã được đổi thành công.')
        return redirect('account_change_password')

    return render(
        request,
        'accounts/change_password.html',
        {
            'form': form,
            'cancel_url': '/customer/profile/',
            'page_description': 'Cập nhật mật khẩu định kỳ để bảo vệ thông tin và các lịch hẹn của bạn.',
        },
    )


@login_required(login_url='/accounts/dang_nhap/')
def staff_change_password_view(request):
    """Change the password for a signed-in staff or administrator account."""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('/home/customer/')

    form = AccountPasswordChangeForm(
        user=request.user,
        data=request.POST if request.method == 'POST' else None,
    )

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Mật khẩu của bạn đã được đổi thành công.')
        return redirect('staff_change_password')

    return render(
        request,
        'accounts/staff_change_password.html',
        {
            'form': form,
            'cancel_url': '/home/staff/',
            'page_description': 'Cập nhật mật khẩu định kỳ để bảo vệ tài khoản nhân viên của bạn.',
        },
    )
