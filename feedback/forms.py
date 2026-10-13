from django import forms
from .models import PhanHoiKhieuNai


class PhanHoiKhieuNaiForm(forms.ModelForm):
    loai_ph = forms.ChoiceField(
        choices=PhanHoiKhieuNai.LOAI_PH_CHOICES,
        widget=forms.RadioSelect,
        label="Bạn muốn gửi"
    )

    class Meta:
        model = PhanHoiKhieuNai
        fields = ['loai_ph', 'ma_dv', 'tieu_de', 'noi_dung']

        widgets = {
            'ma_dv': forms.Select(),
            'tieu_de': forms.TextInput(attrs={
                'placeholder': 'Nhập tiêu đề phản hồi/khiếu nại'
            }),
            'noi_dung': forms.Textarea(attrs={
                'placeholder': 'Nhập nội dung chi tiết...',
                'rows': 6
            }),
        }