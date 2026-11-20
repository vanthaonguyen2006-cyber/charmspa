from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction
from .models import ROLE_CUSTOMER, TaiKhoan
from customers.models import KhachHang, HangThanhVien


class DangKyForm(UserCreationForm):

    ho_ten = forms.CharField(
        max_length=100,
        label="Họ và tên",
        required=True,
        error_messages={
            'required': 'Họ và tên không được để trống.',
            'max_length': 'Họ và tên không được vượt quá 100 ký tự.',
        }
    )

    so_dien_thoai = forms.CharField(
        max_length=15,
        label="Số điện thoại",
        required=True,
        error_messages={
            'required': 'Số điện thoại không được để trống.',
        }
    )

    email = forms.EmailField(
        label="Email",
        required=True,
        error_messages={
            'required': 'Email không được để trống.',
            'invalid': 'Địa chỉ email không đúng định dạng.',
        }
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'username' in self.fields:
            self.fields['username'].error_messages.update({
                'required': 'Tên đăng nhập không được để trống.',
                'unique': 'Tên đăng nhập này đã được sử dụng bởi tài khoản khác.',
                'invalid': 'Tên đăng nhập không hợp lệ.',
            })
        if 'password1' in self.fields:
            self.fields['password1'].error_messages.update({
                'required': 'Vui lòng nhập mật khẩu.',
            })
        if 'password2' in self.fields:
            self.fields['password2'].error_messages.update({
                'required': 'Vui lòng xác nhận mật khẩu.',
            })
        self.error_messages['password_mismatch'] = 'Mật khẩu xác nhận không khớp.'

    # Kiểm tra họ và tên
    def clean_ho_ten(self):
        ho_ten = (self.cleaned_data.get('ho_ten') or '').strip()
        if not ho_ten:
            raise forms.ValidationError("Họ và tên không được để trống.")
        return ho_ten

    # Kiểm tra username
    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise forms.ValidationError("Tên đăng nhập không được để trống.")
        if ' ' in username:
            raise forms.ValidationError("Tên đăng nhập không được chứa khoảng trắng.")

        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                "Tên đăng nhập này đã được sử dụng bởi tài khoản khác."
            )

        return username

    # Kiểm tra số điện thoại
    def clean_so_dien_thoai(self):
        so_dien_thoai = (self.cleaned_data.get('so_dien_thoai') or '').strip()

        if not so_dien_thoai:
            raise forms.ValidationError("Số điện thoại không được để trống.")

        if not so_dien_thoai.isdigit() or not 9 <= len(so_dien_thoai) <= 11:
            raise forms.ValidationError(
                "Số điện thoại không hợp lệ (phải từ 9 đến 11 chữ số)."
            )

        if TaiKhoan.objects.filter(
            so_dien_thoai=so_dien_thoai
        ).exists():
            raise forms.ValidationError(
                "Số điện thoại này đã được sử dụng bởi tài khoản khác."
            )

        return so_dien_thoai

    # Kiểm tra email
    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise forms.ValidationError("Email không được để trống.")

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Email này đã được sử dụng bởi tài khoản khác."
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
            # Lưu User (đảm bảo tài khoản nghiệp vụ không có quyền Django Admin)
            user.is_staff = False
            user.is_superuser = False
            user.save()

            # Tạo tường minh TaiKhoan
            tai_khoan = TaiKhoan.objects.create(
                ma_tk=f"TK{user.id:03d}",
                user=user,
                so_dien_thoai=so_dien_thoai,
                vai_tro=ROLE_CUSTOMER,
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


class AccountPasswordChangeForm(PasswordChangeForm):
    """ĐỔI MK"""

    error_messages = {
        'password_incorrect': 'Mật khẩu hiện tại không chính xác. Vui lòng nhập lại.',
        'password_mismatch': 'Mật khẩu xác nhận không khớp.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = 'Mật khẩu hiện tại'
        self.fields['old_password'].error_messages = {
            'required': 'Vui lòng nhập mật khẩu hiện tại.',
        }
        self.fields['old_password'].widget.attrs.update({
            'autocomplete': 'current-password',
        })
        self.fields['new_password1'].label = 'Mật khẩu mới'
        self.fields['new_password1'].error_messages = {
            'required': 'Vui lòng nhập mật khẩu mới.',
        }
        self.fields['new_password1'].widget.attrs.update({
            'autocomplete': 'new-password',
        })
        self.fields['new_password2'].label = 'Xác nhận mật khẩu mới'
        self.fields['new_password2'].error_messages = {
            'required': 'Vui lòng xác nhận mật khẩu mới.',
        }
        self.fields['new_password2'].widget.attrs.update({
            'autocomplete': 'new-password',
        })
