from django import forms
from datetime import date

# Form nhập khoảng ngày cần khóa & lý do trên trang quản lý ngày hoạt động (admin_activity_day.html).
class KhoaNgayForm(forms.Form):
    # Ngày bắt đầu khóa (DateField dạng input[type="date"]).
    ngay_bat_dau = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'min': date.today().isoformat(),  # Chặn chọn ngày trong quá khứ trên giao diện
            'class': 'w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:border-stone-500'
        }),
        error_messages={'required': 'Vui lòng chọn ngày bắt đầu.'}
    )

    # Ngày kết thúc khóa (DateField dạng input[type="date"]).
    ngay_ket_thuc = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'min': date.today().isoformat(),  # Chặn chọn ngày trong quá khứ trên giao diện
            'class': 'w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:border-stone-500'
        }),
        error_messages={'required': 'Vui lòng chọn ngày kết thúc.'}
    )

    # Dropdown chọn nhóm lý do khóa ngày (chọn 'Khác' thì hiển thị/nhập ô nhap_ly_do).
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

    # Ô nhập lý do chi tiết khi chọn 'Khác' (không bắt buộc ở tầng form, kiểm tra thêm ở view).
    nhap_ly_do = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Nhập chi tiết lý do khóa ngày (nếu chọn Khác)...',
            'class': 'w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:border-stone-500'
        })
    )

    # Hàm kiểm tra ràng buộc logic bảo mật phía server (chặn quá khứ & khoảng ngày ngược).
    def clean(self):
        cleaned_data = super().clean()
        ngay_bat_dau = cleaned_data.get('ngay_bat_dau')
        ngay_ket_thuc = cleaned_data.get('ngay_ket_thuc')
        today = date.today()

        # Không cho phép khóa ngày bắt đầu nhỏ hơn hôm nay.
        if ngay_bat_dau and ngay_bat_dau < today:
            raise forms.ValidationError("Không thể khóa các ngày trong quá khứ!")

        # Không cho phép khóa ngày kết thúc nhỏ hơn hôm nay.
        if ngay_ket_thuc and ngay_ket_thuc < today:
            raise forms.ValidationError("Ngày kết thúc không được nhỏ hơn ngày hiện tại.")

        # Đảm bảo khoảng ngày hợp lệ: ngày bắt đầu <= ngày kết thúc.
        if ngay_bat_dau and ngay_ket_thuc and ngay_bat_dau > ngay_ket_thuc:
            raise forms.ValidationError("Ngày bắt đầu không được lớn hơn ngày kết thúc.")

        return cleaned_data