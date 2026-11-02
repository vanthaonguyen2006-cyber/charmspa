from django import forms
from .models import YeuCauTuVan

class YeuCauTuVanForm(forms.ModelForm):
    class Meta:
        model = YeuCauTuVan
        fields = ['noi_dung'] # Lấy đúng trường noi_dung trong model của bạn
        widgets = {
            'noi_dung': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập vấn đề bạn cần tư vấn (ví dụ: tư vấn gói massage cổ vai gáy)...',
                'rows': 3,
                'style': 'width: 100%; border-radius: 8px; margin-bottom: 10px;'
            }),
        }
        labels = {
            'noi_dung': '' # Ẩn tên nhãn để giao diện chat gọn hơn
        }