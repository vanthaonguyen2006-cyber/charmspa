from django import forms
from datetime import date


class KhoaNgayForm(forms.Form):
    ngay_bat_dau = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'min': date.today().isoformat(),  # Chặn chọn ngày trong quá khứ trên giao diện
            'class': 'w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:border-stone-500'
        }),
        error_messages={'required': 'Vui lòng chọn ngày bắt đầu.'}
    )

    ngay_ket_thuc = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'min': date.today().isoformat(),  # Chặn chọn ngày trong quá khứ trên giao diện
            'class': 'w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:border-stone-500'
        }),
        error_messages={'required': 'Vui lòng chọn ngày kết thúc.'}
    )

    ly_do = forms.ChoiceField(
        choices=[
            ('Nghỉ lễ', 'Nghỉ lễ'),
            ('Nghỉ bảo trì', 'Nghỉ bảo trì'),
            ('Nghỉ đột xuất', 'Nghỉ đột xuất'),
            ('Khác', 'Lý do khác')
        ],
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:border-stone-500'
        })
    )

    nhap_ly_do = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Nhập chi tiết lý do khóa ngày (nếu chọn Khác)...',
            'class': 'w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:border-stone-500'
        })
    )

    # Hàm kiểm tra ràng buộc logic bảo mật phía server
    def clean(self):
        cleaned_data = super().clean()
        ngay_bat_dau = cleaned_data.get('ngay_bat_dau')
        ngay_ket_thuc = cleaned_data.get('ngay_ket_thuc')
        today = date.today()

        if ngay_bat_dau and ngay_bat_dau < today:
            raise forms.ValidationError("Không thể khóa các ngày trong quá khứ!")

        if ngay_ket_thuc and ngay_ket_thuc < today:
            raise forms.ValidationError("Ngày kết thúc không được nhỏ hơn ngày hiện tại.")

        if ngay_bat_dau and ngay_ket_thuc and ngay_bat_dau > ngay_ket_thuc:
            raise forms.ValidationError("Ngày bắt đầu không được lớn hơn ngày kết thúc.")

        return cleaned_data