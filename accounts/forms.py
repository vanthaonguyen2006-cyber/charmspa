from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from .models import TaiKhoan
from customers.models import KhachHang, HangThanhVien


class DangKyForm(forms.ModelForm):
    ho_ten = forms.CharField(
        max_length=100,
        label="Họ và tên",
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Nhập họ và tên đầy đủ'})
    )
    so_dien_thoai = forms.CharField(
        max_length=15,
        label="Số điện thoại",
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Nhập số điện thoại'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Nhập mật khẩu'}),
        label="Mật khẩu",
        required=True
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Xác nhận lại mật khẩu'}),
        label="Xác nhận mật khẩu",
        required=True
    )

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Tên đăng nhập'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Địa chỉ email'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Tên đăng nhập này đã được sử dụng. Vui lòng chọn tên khác.")
        return username

    def clean_so_dien_thoai(self):
        so_dien_thoai = self.cleaned_data.get('so_dien_thoai', '').strip()
        if not so_dien_thoai.isdigit() or len(so_dien_thoai) < 9 or len(so_dien_thoai) > 11:
            raise forms.ValidationError("Số điện thoại không hợp lệ (phải từ 9 đến 11 chữ số).")

        if TaiKhoan.objects.filter(so_dien_thoai=so_dien_thoai).exists():
            raise forms.ValidationError("Số điện thoại này đã được đăng ký tài khoản.")
        return so_dien_thoai

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email này đã được sử dụng cho một tài khoản khác.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Mật khẩu xác nhận không khớp!")
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        cleaned_data = self.cleaned_data

        # 1. Khởi tạo đối tượng User và gắn kèm thuộc tính tạm để Signal nhận diện
        user = User(
            username=cleaned_data['username'],
            email=cleaned_data.get('email', '')
        )
        user.set_password(cleaned_data['password'])
        # Thuộc tính này sẽ được Signal `dong_bo_tai_khoan_va_vai_tro` đọc ngay trong sự kiện post_save
        user._so_dien_thoai_dang_ky = cleaned_data['so_dien_thoai']
        user.save()

        # 2. Lấy bản ghi TaiKhoan vừa được Signal tạo (hoặc tạo dự phòng nếu Signal chưa chạy)
        ma_tk_str = f"TK{user.id:03d}"
        tai_khoan, created_tk = TaiKhoan.objects.get_or_create(
            user=user,
            defaults={
                'ma_tk': ma_tk_str,
                'so_dien_thoai': cleaned_data['so_dien_thoai'],
                'vai_tro': "Khách hàng"
            }
        )
        # Đồng bộ chắc chắn số điện thoại nếu bản ghi đã tồn tại từ trước
        if not created_tk and tai_khoan.so_dien_thoai != cleaned_data['so_dien_thoai']:
            tai_khoan.so_dien_thoai = cleaned_data['so_dien_thoai']
            tai_khoan.vai_tro = "Khách hàng"
            tai_khoan.save(update_fields=['so_dien_thoai', 'vai_tro'])

        # 3. Lấy hạng thành viên mặc định (ngưỡng điểm thấp nhất)
        hang_mac_dinh = HangThanhVien.objects.order_by('diem_toi_thieu').first()

        # 4. Tạo hồ sơ KhachHang liên kết OneToOne với TaiKhoan
        ma_kh_str = f"KH{user.id:03d}"
        KhachHang.objects.get_or_create(
            ma_tk=tai_khoan,
            defaults={
                'ma_kh': ma_kh_str,
                'ho_ten': cleaned_data['ho_ten'],
                'ma_tv': hang_mac_dinh,
                'diem_tich_luy_kh': 0
            }
        )

        return user


class DangNhapForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label="Tên đăng nhập, email hoặc số điện thoại",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập username, email hoặc SĐT'})
    )
    password = forms.CharField(
        label="Mật khẩu",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập mật khẩu'})
    )


# =========================================================================
# FORM THÊM MỚI NHÂN VIÊN & CHỈNH SỬA TÀI KHOẢN (CHO TRANG QUẢN TRỊ NGƯỜI DÙNG)
# =========================================================================
from django import forms
from django.contrib.auth.models import User
from .models import TaiKhoan


class ThemNhanVienForm(forms.Form):
    VAI_TRO_CHOICES = [
        ('Nhân viên CSKH', 'Nhân viên CSKH'),
        ('Chuyên viên', 'Chuyên viên'),
        ('Quản trị viên', 'Quản trị viên'),
    ]
    TRANG_THAI_CHOICES = [
        ('Hoạt động', 'Hoạt động'),
        ('Đã khóa', 'Đã khóa'),
    ]

    ho_ten = forms.CharField(max_length=100, required=True, label="Họ và tên")
    so_dien_thoai = forms.CharField(max_length=15, required=True, label="Số điện thoại")
    email = forms.EmailField(required=True, label="Email")
    ngay_sinh = forms.DateField(required=False, label="Ngày sinh", input_formats=['%Y-%m-%d', '%d/%m/%Y'])
    username = forms.CharField(max_length=150, required=True, label="Tên đăng nhập")
    vai_tro = forms.ChoiceField(choices=VAI_TRO_CHOICES, required=True, label="Vai trò")
    password = forms.CharField(widget=forms.PasswordInput, required=True, label="Mật khẩu")
    password_confirm = forms.CharField(widget=forms.PasswordInput, required=True, label="Xác nhận mật khẩu")
    trang_thai = forms.ChoiceField(choices=TRANG_THAI_CHOICES, initial='Hoạt động', label="Trạng thái")

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Tên đăng nhập này đã tồn tại trong hệ thống.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Địa chỉ email này đã được sử dụng.")
        return email

    def clean_so_dien_thoai(self):
        sdt = self.cleaned_data.get('so_dien_thoai', '').strip()
        if not sdt.isdigit() or len(sdt) < 9 or len(sdt) > 11:
            raise forms.ValidationError("Số điện thoại không hợp lệ (phải từ 9 đến 11 số).")
        if TaiKhoan.objects.filter(so_dien_thoai=sdt).exists():
            raise forms.ValidationError("Số điện thoại này đã được sử dụng cho tài khoản khác.")
        return sdt

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        pwc = cleaned_data.get('password_confirm')
        if pw and pwc and pw != pwc:
            raise forms.ValidationError("Mật khẩu xác nhận không khớp!")
        if pw and len(pw) < 6:
            raise forms.ValidationError("Mật khẩu phải có độ dài tối thiểu 6 ký tự.")
        return cleaned_data


class ChinhSuaTaiKhoanForm(forms.Form):
    VAI_TRO_CHOICES = [
        ('Admin', 'Admin'),
        ('Nhân viên CSKH', 'Nhân viên CSKH'),
        ('Chuyên viên', 'Chuyên viên'),
        ('Khách hàng', 'Khách hàng'),
    ]
    TRANG_THAI_CHOICES = [
        ('Hoạt động', 'Hoạt động'),
        ('Đã khóa', 'Đã khóa'),
    ]

    ho_ten = forms.CharField(max_length=100, required=False, label="Họ và tên")
    so_dien_thoai = forms.CharField(max_length=15, required=True, label="Số điện thoại")
    email = forms.EmailField(required=False, label="Email")
    vai_tro = forms.ChoiceField(choices=VAI_TRO_CHOICES, required=True, label="Vai trò")
    trang_thai = forms.ChoiceField(choices=TRANG_THAI_CHOICES, required=True, label="Trạng thái tài khoản")
