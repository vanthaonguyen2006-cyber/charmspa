from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.db import transaction
from .models import TaiKhoan
from customers.models import KhachHang, HangThanhVien
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

class DangKyForm(UserCreationForm):

    ho_ten = forms.CharField(
        max_length=100,
        label="Họ và tên",
        required=True
    )

    so_dien_thoai = forms.CharField(
        max_length=15,
        label="Số điện thoại",
        required=True
    )

    email = forms.EmailField(
        label="Email",
        required=True
    )

    dong_y_dieu_khoan = forms.BooleanField(
        required=True,
        error_messages={
            'required': 'Bạn cần đồng ý với điều khoản sử dụng.'
        }
    )

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password1',
            'password2'
        ]

    # Kiểm tra username
    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()

        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                "Tên đăng nhập đã tồn tại!"
            )

        return username

    # Kiểm tra số điện thoại
    def clean_so_dien_thoai(self):
        so_dien_thoai = self.cleaned_data.get(
            'so_dien_thoai', ''
        ).strip()

        if not so_dien_thoai.isdigit() or not 9 <= len(so_dien_thoai) <= 11:
            raise forms.ValidationError(
                "Số điện thoại phải có từ 9 đến 11 chữ số!"
            )

        if TaiKhoan.objects.filter(
            so_dien_thoai=so_dien_thoai
        ).exists():
            raise forms.ValidationError(
                "Số điện thoại đã được sử dụng!"
            )

        return so_dien_thoai

    # Kiểm tra email
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Email đã được sử dụng!"
            )

        return email

    # Tạo tài khoản và hồ sơ khách hàng
    @transaction.atomic
    def save(self, commit=True):

        user = super().save(commit=False)

        # Lấy thông tin từ Form
        so_dien_thoai = self.cleaned_data['so_dien_thoai']
        ho_ten = self.cleaned_data['ho_ten']

        # Kiểm tra hạng thành viên mặc định
        hang_mac_dinh = HangThanhVien.objects.order_by(
            'diem_toi_thieu'
        ).first()

        if hang_mac_dinh is None:
            raise forms.ValidationError(
                "Chưa có hạng thành viên trong hệ thống!"
            )

        if commit:
            # Cung cấp số điện thoại cho Signal
            user._so_dien_thoai_dang_ky = so_dien_thoai

            # Lưu User
            user.save()

            # Tạo hoặc lấy TaiKhoan
            ma_tk_str = f"TK{user.id:03d}"

            tai_khoan, created_tk = TaiKhoan.objects.get_or_create(
                user=user,
                defaults={
                    'ma_tk': ma_tk_str,
                    'so_dien_thoai': so_dien_thoai,
                    'vai_tro': 'Khách hàng'
                }
            )

            # Tạo hồ sơ khách hàng
            ma_kh_str = f"KH{user.id:03d}"

            KhachHang.objects.get_or_create(
                ma_tk=tai_khoan,
                defaults={
                    'ma_kh': ma_kh_str,
                    'ho_ten': ho_ten,
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


class AccountPasswordChangeForm(PasswordChangeForm):
    """Django's password change form with Vietnamese account-facing labels."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = 'Mật khẩu hiện tại'
        self.fields['old_password'].widget.attrs.update({
            'autocomplete': 'current-password',
        })
        self.fields['new_password1'].label = 'Mật khẩu mới'
        self.fields['new_password1'].widget.attrs.update({
            'autocomplete': 'new-password',
        })
        self.fields['new_password2'].label = 'Xác nhận mật khẩu mới'
        self.fields['new_password2'].widget.attrs.update({
            'autocomplete': 'new-password',
        })
