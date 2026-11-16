from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from accounts.models import (
    ASSIGNABLE_ROLES,
    ROLE_CHOICES,
    ROLE_CUSTOMER,
    ROLE_MANAGER,
    ROLE_STAFF,
    TaiKhoan,
    normalize_role,
)


class ThemKhachHangForm(forms.Form):
    GIOI_TINH_CHOICES = [
        ('Nam', 'Nam'),
        ('Nữ', 'Nữ'),
        ('Khác', 'Khác'),
    ]

    ho_ten = forms.CharField(
        max_length=100,
        required=True,
        error_messages={'required': 'Vui lòng nhập họ và tên khách hàng.'}
    )
    so_dien_thoai = forms.CharField(
        max_length=15,
        required=True,
        error_messages={'required': 'Vui lòng nhập số điện thoại.'}
    )
    email = forms.EmailField(
        required=False,
        error_messages={'invalid': 'Địa chỉ email không đúng định dạng.'}
    )
    ngay_sinh = forms.DateField(
        required=False,
        input_formats=['%Y-%m-%d', '%d/%m/%Y'],
        error_messages={'invalid': 'Ngày sinh không hợp lệ (định dạng YYYY-MM-DD hoặc DD/MM/YYYY).'}
    )
    gioi_tinh = forms.ChoiceField(
        choices=GIOI_TINH_CHOICES,
        initial='Nam',
        required=True,
        error_messages={'required': 'Vui lòng chọn giới tính.'}
    )

    def clean_ho_ten(self):
        ho_ten = self.cleaned_data.get('ho_ten', '').strip()
        if not ho_ten:
            raise forms.ValidationError("Họ và tên không được để trống.")
        return ho_ten

    def clean_so_dien_thoai(self):
        sdt = self.cleaned_data.get('so_dien_thoai', '').strip()
        if not sdt.isdigit() or len(sdt) < 9 or len(sdt) > 11:
            raise forms.ValidationError("Số điện thoại không hợp lệ (phải từ 9 đến 11 số).")
        if TaiKhoan.objects.filter(so_dien_thoai=sdt).exists():
            raise forms.ValidationError("Số điện thoại này đã được sử dụng cho tài khoản khác.")
        return sdt


class ThemNhanVienForm(forms.Form):
    VAI_TRO_CHOICES = [
        (ROLE_STAFF, ROLE_STAFF),
        (ROLE_MANAGER, ROLE_MANAGER),
    ]
    GIOI_TINH_CHOICES = [
        ('Nữ', 'Nữ'),
        ('Nam', 'Nam'),
        ('Khác', 'Khác'),
    ]

    ho_ten = forms.CharField(
        max_length=100,
        required=True,
        error_messages={'required': 'Vui lòng nhập họ và tên.'}
    )
    gioi_tinh = forms.ChoiceField(
        choices=GIOI_TINH_CHOICES,
        initial='Nữ',
        required=True,
        error_messages={'required': 'Vui lòng chọn giới tính.'}
    )
    so_dien_thoai = forms.CharField(
        max_length=15,
        required=True,
        error_messages={'required': 'Vui lòng nhập số điện thoại.'}
    )
    email = forms.EmailField(
        required=True,
        error_messages={
            'required': 'Vui lòng nhập địa chỉ email.',
            'invalid': 'Địa chỉ email không đúng định dạng.'
        }
    )
    ngay_sinh = forms.DateField(
        required=False,
        input_formats=['%Y-%m-%d', '%d/%m/%Y'],
        error_messages={'invalid': 'Ngày sinh không hợp lệ (định dạng YYYY-MM-DD).'}
    )
    vai_tro = forms.ChoiceField(
        choices=VAI_TRO_CHOICES,
        initial=ROLE_STAFF,
        required=True,
        error_messages={
            'required': 'Vui lòng chọn vai trò.',
            'invalid_choice': 'Chỉ được tạo tài khoản nhân sự với vai trò Nhân viên hoặc Quản lý.',
        }
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        error_messages={'required': 'Vui lòng nhập tên đăng nhập.'}
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        error_messages={'required': 'Vui lòng nhập mật khẩu.'}
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        error_messages={'required': 'Vui lòng xác nhận mật khẩu.'}
    )

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

    def clean_vai_tro(self):
        vai_tro = normalize_role(self.cleaned_data.get('vai_tro'))
        if vai_tro not in ASSIGNABLE_ROLES:
            raise forms.ValidationError("Chỉ được phép chọn vai trò Nhân viên hoặc Quản lý.")
        return vai_tro

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        pwc = cleaned_data.get('password_confirm')

        if pw and len(pw) < 6:
            self.add_error('password', "Mật khẩu phải có độ dài tối thiểu 6 ký tự.")

        if pw and pwc and pw != pwc:
            self.add_error('password_confirm', "Mật khẩu xác nhận không khớp!")

        return cleaned_data


class ChinhSuaTaiKhoanForm(forms.Form):
    VAI_TRO_CHOICES = list(ROLE_CHOICES)
    GIOI_TINH_CHOICES = [
        ('Nam', 'Nam'),
        ('Nữ', 'Nữ'),
        ('Khác', 'Khác'),
    ]

    ho_ten = forms.CharField(
        max_length=100,
        required=True,
        error_messages={'required': 'Họ và tên không được để trống.'}
    )
    so_dien_thoai = forms.CharField(
        max_length=15,
        required=True,
        error_messages={'required': 'Số điện thoại không được để trống.'}
    )
    email = forms.EmailField(
        required=True,
        error_messages={
            'required': 'Email không được để trống.',
            'invalid': 'Địa chỉ email không đúng định dạng.'
        }
    )
    vai_tro = forms.CharField(
        required=False,
        error_messages={'required': 'Vui lòng chọn vai trò.'}
    )
    gioi_tinh = forms.ChoiceField(
        choices=GIOI_TINH_CHOICES,
        required=True,
        error_messages={'required': 'Vui lòng chọn giới tính.'}
    )
    ngay_sinh = forms.DateField(
        required=False,
        input_formats=['%Y-%m-%d', '%d/%m/%Y'],
        error_messages={'invalid': 'Ngày sinh không hợp lệ.'}
    )

    def __init__(self, *args, current_role=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_role = normalize_role(current_role)

    def clean_ho_ten(self):
        ho_ten = self.cleaned_data.get('ho_ten', '').strip()
        if not ho_ten:
            raise forms.ValidationError("Họ và tên không được chỉ chứa khoảng trắng.")
        return ho_ten

    def clean_so_dien_thoai(self):
        sdt = self.cleaned_data.get('so_dien_thoai', '').strip()
        if not sdt.isdigit() or len(sdt) < 9 or len(sdt) > 11:
            raise forms.ValidationError("Số điện thoại không hợp lệ (phải từ 9 đến 11 chữ số).")
        return sdt

    def clean_vai_tro(self):
        raw_val = (self.cleaned_data.get('vai_tro') or '').strip()
        vai_tro_moi = normalize_role(raw_val) if raw_val else self.current_role

        if not vai_tro_moi:
            raise forms.ValidationError("Vai trò không hợp lệ.")

        if self.current_role == ROLE_CUSTOMER:
            if vai_tro_moi != ROLE_CUSTOMER:
                raise forms.ValidationError("Không được thay đổi vai trò của tài khoản Khách hàng.")
            return ROLE_CUSTOMER

        if vai_tro_moi not in ASSIGNABLE_ROLES:
            raise forms.ValidationError("Chỉ được phân quyền qua lại giữa Nhân viên và Quản lý.")
        return vai_tro_moi

    def clean_ngay_sinh(self):
        ngay_sinh = self.cleaned_data.get('ngay_sinh')
        if ngay_sinh and ngay_sinh > timezone.localdate():
            raise forms.ValidationError("Ngày sinh không được lớn hơn ngày hiện tại.")
        return ngay_sinh


class ChinhSuaHoSoKhachHangForm(forms.Form):
    GIOI_TINH_CHOICES = [
        ('', 'Chưa cập nhật'),
        ('Nam', 'Nam'),
        ('Nữ', 'Nữ'),
        ('Khác', 'Khác'),
    ]

    ho_ten = forms.CharField(
        max_length=100,
        required=True,
        error_messages={'required': 'Họ và tên không được để trống.'}
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        error_messages={'required': 'Tên đăng nhập không được để trống.'}
    )
    so_dien_thoai = forms.CharField(
        max_length=15,
        required=True,
        error_messages={'required': 'Số điện thoại không được để trống.'}
    )
    email = forms.EmailField(
        required=False,
        error_messages={'invalid': 'Địa chỉ email không đúng định dạng.'}
    )
    ngay_sinh = forms.DateField(
        required=False,
        input_formats=['%Y-%m-%d', '%d/%m/%Y'],
        error_messages={'invalid': 'Ngày sinh không hợp lệ.'}
    )
    gioi_tinh = forms.ChoiceField(
        choices=GIOI_TINH_CHOICES,
        required=False,
        error_messages={'invalid_choice': 'Giới tính không hợp lệ.'}
    )

    def __init__(self, *args, current_user=None, current_tai_khoan=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = current_user
        self.current_tai_khoan = current_tai_khoan

    def clean_ho_ten(self):
        ho_ten = self.cleaned_data.get('ho_ten', '').strip()
        if not ho_ten:
            raise forms.ValidationError("Họ và tên không được chỉ chứa khoảng trắng.")
        return ho_ten

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise forms.ValidationError("Tên đăng nhập không được để trống.")
        if ' ' in username:
            raise forms.ValidationError("Tên đăng nhập không được chứa khoảng trắng.")
        qs = User.objects.filter(username__iexact=username)
        if self.current_user and self.current_user.pk:
            qs = qs.exclude(pk=self.current_user.pk)
        if qs.exists():
            raise forms.ValidationError("Tên đăng nhập này đã được sử dụng bởi tài khoản khác.")
        return username

    def clean_so_dien_thoai(self):
        sdt = self.cleaned_data.get('so_dien_thoai', '').strip()
        if not sdt:
            raise forms.ValidationError("Số điện thoại không được để trống.")
        if not sdt.isdigit() or len(sdt) < 9 or len(sdt) > 11:
            raise forms.ValidationError("Số điện thoại chỉ chứa chữ số, từ 9–11 số.")
        qs = TaiKhoan.objects.filter(so_dien_thoai=sdt)
        if self.current_tai_khoan and self.current_tai_khoan.pk:
            qs = qs.exclude(pk=self.current_tai_khoan.pk)
        if qs.exists():
            raise forms.ValidationError("Số điện thoại này đã được sử dụng bởi tài khoản khác.")
        return sdt

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email:
            qs = User.objects.filter(email__iexact=email)
            if self.current_user and self.current_user.pk:
                qs = qs.exclude(pk=self.current_user.pk)
            if qs.exists():
                raise forms.ValidationError("Email này đã được sử dụng bởi tài khoản khác.")
        return email

    def clean_ngay_sinh(self):
        ngay_sinh = self.cleaned_data.get('ngay_sinh')
        if ngay_sinh:
            today = timezone.localdate()
            if ngay_sinh > today:
                raise forms.ValidationError("Ngày sinh không được lớn hơn ngày hiện tại.")
        return ngay_sinh

    def clean_gioi_tinh(self):
        gioi_tinh = self.cleaned_data.get('gioi_tinh', '').strip()
        if gioi_tinh and gioi_tinh not in ('Nam', 'Nữ', 'Khác'):
            raise forms.ValidationError("Giới tính không hợp lệ theo hệ thống.")
        return gioi_tinh


class StaffProfileUpdateForm(forms.Form):
    """Form cập nhật thông tin cá nhân cho Nhân viên và Quản lý (không sửa quyền/hệ thống)."""

    GIOI_TINH_CHOICES = [
        ('Nam', 'Nam'),
        ('Nữ', 'Nữ'),
        ('Khác', 'Khác'),
    ]

    ho_ten = forms.CharField(
        max_length=100,
        required=True,
        error_messages={
            'required': 'Vui lòng nhập họ và tên.',
            'max_length': 'Họ và tên không được vượt quá 100 ký tự.',
        }
    )
    so_dien_thoai = forms.CharField(
        max_length=15,
        required=True,
        error_messages={'required': 'Vui lòng nhập số điện thoại.'}
    )
    email = forms.EmailField(
        required=True,
        error_messages={
            'required': 'Vui lòng nhập địa chỉ email.',
            'invalid': 'Địa chỉ email không đúng định dạng.',
        }
    )
    ngay_sinh = forms.DateField(
        required=False,
        input_formats=['%Y-%m-%d', '%d/%m/%Y'],
        error_messages={'invalid': 'Ngày sinh không hợp lệ.'}
    )
    gioi_tinh = forms.ChoiceField(
        choices=GIOI_TINH_CHOICES,
        required=True,
        error_messages={
            'required': 'Vui lòng chọn giới tính.',
            'invalid_choice': 'Giới tính không hợp lệ.',
        }
    )

    def __init__(self, *args, current_user=None, current_tai_khoan=None, has_nhan_vien=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = current_user
        self.current_tai_khoan = current_tai_khoan
        self.has_nhan_vien = has_nhan_vien

    def clean_ho_ten(self):
        ho_ten = (self.cleaned_data.get('ho_ten') or '').strip()
        if not ho_ten:
            raise forms.ValidationError('Họ và tên không được chỉ chứa khoảng trắng.')
        return ho_ten

    def clean_so_dien_thoai(self):
        sdt = (self.cleaned_data.get('so_dien_thoai') or '').strip()
        if not sdt.isdigit() or len(sdt) < 9 or len(sdt) > 11:
            raise forms.ValidationError('Số điện thoại không hợp lệ (phải từ 9 đến 11 chữ số).')

        qs = TaiKhoan.objects.filter(so_dien_thoai=sdt)
        if self.current_tai_khoan and self.current_tai_khoan.pk:
            qs = qs.exclude(pk=self.current_tai_khoan.pk)
        if qs.exists():
            raise forms.ValidationError('Số điện thoại này đã được sử dụng bởi tài khoản khác.')
        return sdt

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise forms.ValidationError('Vui lòng nhập địa chỉ email.')

        qs = User.objects.filter(email__iexact=email)
        if self.current_user and self.current_user.pk:
            qs = qs.exclude(pk=self.current_user.pk)
        if qs.exists():
            raise forms.ValidationError('Địa chỉ email này đã được sử dụng bởi tài khoản khác.')
        return email

    def clean_ngay_sinh(self):
        ngay_sinh = self.cleaned_data.get('ngay_sinh')
        if self.has_nhan_vien and not ngay_sinh:
            raise forms.ValidationError('Vui lòng chọn ngày sinh.')
        if ngay_sinh and ngay_sinh > timezone.localdate():
            raise forms.ValidationError('Ngày sinh không được lớn hơn ngày hiện tại.')
        return ngay_sinh

    def clean_gioi_tinh(self):
        gioi_tinh = (self.cleaned_data.get('gioi_tinh') or '').strip()
        if gioi_tinh not in ('Nam', 'Nữ', 'Khác'):
            raise forms.ValidationError('Giới tính không hợp lệ.')
        return gioi_tinh
