from django import forms
from django.contrib.auth.password_validation import validate_password
from .models import TaiKhoan

class DangKyForm(forms.ModelForm):
    # Khai báo ô mật khẩu và xác nhận mật khẩu
    mat_khau = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Nhập mật khẩu'}),
        label="Mật khẩu"
    )
    xac_nhan_mat_khau = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Nhập lại mật khẩu'}),
        label="Xác nhận mật khẩu"
    )

    class Meta:
        model = TaiKhoan
        # Bổ sung 'username' vào đây để người dùng tự điền
        fields = ['username', 'email', 'so_dien_thoai']

    # Kiểm tra điều kiện bảo mật mật khẩu
    def clean_mat_khau(self):
        mat_khau = self.cleaned_data.get('mat_khau')
        try:
            validate_password(mat_khau)
        except forms.ValidationError as e:
            raise forms.ValidationError(e.messages)
        return mat_khau

    # Kiểm tra xác nhận mật khẩu có khớp nhau không
    def clean(self):
        cleaned_data = super().clean()
        mat_khau = cleaned_data.get("mat_khau")
        xac_nhan_mat_khau = cleaned_data.get("xac_nhan_mat_khau")

        if mat_khau and xac_nhan_mat_khau and mat_khau != xac_nhan_mat_khau:
            raise forms.ValidationError("Mật khẩu xác nhận không trùng khớp!")
        return cleaned_data



class DangNhapForm(forms.Form):
    username = forms.CharField(
        label="Tên đăng nhập hoặc Email",
        widget=forms.TextInput(attrs={'placeholder': 'Nhập tên đăng nhập'})
    )
    mat_khau = forms.CharField(
        label="Mật khẩu",
        widget=forms.PasswordInput(attrs={'placeholder': 'Nhập mật khẩu'})
    )