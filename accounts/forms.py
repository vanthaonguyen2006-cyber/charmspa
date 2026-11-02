from django import forms
from django.contrib.auth.models import User
from .models import TaiKhoan
from customers.models import KhachHang


# 1. Form Đăng Ký (Gắn kết đồng bộ User, TaiKhoan và KhachHang)
from django import forms
from django.contrib.auth.models import User
from .models import TaiKhoan
from customers.models import KhachHang


class DangKyForm(forms.ModelForm):
    ho_ten = forms.CharField(max_length=100, label="Họ và tên", required=True)
    so_dien_thoai = forms.CharField(max_length=10, label="Số điện thoại", required=True)
    password = forms.CharField(widget=forms.PasswordInput, label="Mật khẩu",required=True)
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Xác nhận mật khẩu",required=True)

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Mật khẩu xác nhận không khớp!")
        return cleaned_data

    def save(self, commit=True):
        cleaned_data = self.cleaned_data

        # 1. Tạo User chuẩn của Django
        user = User.objects.create_user(
            username=cleaned_data['username'],
            email=cleaned_data['email'],
            password=cleaned_data['password']
        )

        # 2. Tạo bản ghi TaiKhoan
        ma_tk_str = f"TK{user.id:03d}"
        tai_khoan = TaiKhoan.objects.create(
            ma_tk=ma_tk_str,
            user=user,
            so_dien_thoai=cleaned_data['so_dien_thoai'],
            vai_tro="Khách hàng"
        )

        # 3. QUAN TRỌNG: Lấy đúng biến 'ho_ten' từ form ném vào bảng KhachHang
        ma_kh_str = f"KH{user.id:03d}"
        KhachHang.objects.create(
            ma_kh=ma_kh_str,
            ma_tk=tai_khoan,
            ho_ten=cleaned_data['ho_ten']  # Đảm bảo trường này khớp với model KhachHang
        )

        return user

# 2. Form Đăng Nhập (Hỗ trợ nhập Username hoặc Số điện thoại/Email)
class DangNhapForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label="Email hoặc số điện thoại",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập thông tin đăng nhập'})
    )
    password = forms.CharField(
        label="Mật khẩu",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập mật khẩu'})
    )