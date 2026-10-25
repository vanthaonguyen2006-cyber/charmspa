from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from customers.models import KhachHang

@login_required(login_url='/accounts/dang_nhap/')
def customer_profile_view(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect('/home/staff/')

    khach_hang = KhachHang.objects.filter(ma_tk__user=request.user).first()
    tai_khoan = getattr(request.user, 'tai_khoan', None)
    lich_su_dich_vu = []

    if khach_hang:
        try:
            lich_su_dich_vu = khach_hang.lichsudichvu_set.all()[:4]
        except Exception:
            lich_su_dich_vu = []

    # XỬ LÝ KHI BẤM "LƯU THAY ĐỔI"
    if request.method == 'POST':
        ho_ten_moi = request.POST.get('ho_ten')
        sdt_moi = request.POST.get('so_dien_thoai')
        email_moi = request.POST.get('email')
        ngay_sinh_moi = request.POST.get('ngay_sinh')

        # 1. Cập nhật User (Email)
        if email_moi:
            request.user.email = email_moi
            request.user.save()

        # 2. Cập nhật KhachHang (CHỈ cho sửa Họ tên và Ngày sinh. Nguồn khách & Chuyên viên giữ nguyên!)
        if khach_hang:
            khach_hang.ho_ten = ho_ten_moi
            khach_hang.ngay_sinh = ngay_sinh_moi if ngay_sinh_moi else None
            khach_hang.save()

        # 3. Cập nhật TaiKhoan (Số điện thoại)
        if tai_khoan and sdt_moi:
            tai_khoan.so_dien_thoai = sdt_moi
            tai_khoan.save()

        return redirect('customer_profile')

    is_editing = request.GET.get('edit') == 'true'

    if not khach_hang:
        class TempKhachHang:
            ho_ten = request.user.get_full_name() or request.user.username
            ngay_sinh = None
            nguon_khach = ""
            chuyen_vien_uu_tien = ""
            @property
            def ma_tk(self):
                class DummyTk:
                    so_dien_thoai = ""
                return DummyTk()
            diem_tich_luy_kh = 0
            ma_tv = None

        khach_hang = TempKhachHang()

    context = {
        'khach_hang': khach_hang,
        'lich_su_dich_vu': lich_su_dich_vu,
        'is_editing': is_editing,
    }

    return render(request, 'customer/customer_profile.html', context)


from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required


@login_required(login_url='/accounts/dang_nhap/')
def customer_lock_account_view(request):
    if request.method == 'POST':
        ly_do = request.POST.get('ly_do')
        ly_do_khac = request.POST.get('ly_do_khac', '')

        # Ghi nhận lý do khóa nếu cần lưu vào log/database (tuỳ chọn)
        # Ví dụ: thiet_lap_trang_thai_khoa(...)

        # Khóa tài khoản Django User (is_active = False)
        user = request.user
        user.is_active = False
        user.save()

        # Nếu model TaiKhoan có trường trạng thái, cập nhật luôn ở đây
        tai_khoan = getattr(user, 'tai_khoan', None)
        if tai_khoan:
            tai_khoan.trang_thai = "Đã khóa"
            tai_khoan.save()

        # Đăng xuất người dùng ngay lập tức
        logout(request)

        # Chuyển hướng về trang đăng nhập hoặc trang chủ kèm thông báo
        return redirect('/accounts/dang_nhap/')

    return redirect('customer_profile')


from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from accounts.models import LichSuTaiKhoan # Import model lịch sử tài khoản của app accounts


@login_required(login_url='/accounts/dang_nhap/')
def customer_lock_account_view(request):
    if request.method == 'POST':
        ly_do_chon = request.POST.get('ly_do')
        ly_do_khac = request.POST.get('ly_do_khac', '')

        # Nếu chọn "Lý do khác" thì lấy nội dung trong ô text, ngược lại lấy lý do được chọn
        ly_do_chi_tiet = ly_do_khac if ly_do_chon == 'Lý do khác' and ly_do_khac else ly_do_chon

        user = request.user
        tai_khoan_hien_tai = getattr(user, 'tai_khoan',
                                     None)  # Hoặc thong_tin_tai_khoan tùy related_name trong TaiKhoan model

        if tai_khoan_hien_tai:
            # 1. Tự động sinh mã lịch sử mới (Ví dụ: LS001, LS002,...)
            count_ls = LichSuTaiKhoan.objects.count() + 1
            ma_ls_str = f"LS{count_ls:03d}"

            # 2. Ghi vào bảng LICH_SU_TAI_KHOAN theo đúng cấu trúc model của bạn
            LichSuTaiKhoan.objects.create(
                ma_ls=ma_ls_str,
                ma_tk=tai_khoan_hien_tai,  # Tài khoản bị khóa
                ma_tk_thuc_hien=tai_khoan_hien_tai,  # Khách hàng tự khóa tài khoản của chính mình
                hanh_dong="Khóa",
                ly_do=ly_do_chi_tiet
            )

        # 3. Vô hiệu hóa tài khoản Django User
        user.is_active = False
        user.save()

        # 4. Đăng xuất tài khoản ngay lập tức
        logout(request)

        return redirect('/accounts/dang_nhap/')

    return redirect('customer_profile')