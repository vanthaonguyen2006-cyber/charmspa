import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'charmspa.settings')
django.setup()

from services.models import DichVu

danh_sach_con_lai = [
    {
        "ma_dv": "DV05",
        "ten_dich_vu": "Herbal Therapy at Charm Spa Massage Da Nang",
        "loai_dich_vu": "Massage thảo dược",
        "thoi_luong": 90,
        "suc_chua_toi_da": 30,
        "diem_tich_luy_dich_vu": 90,
        "gia_dich_vu": 900000,
        "mo_ta": "Liệu pháp thảo dược thiên nhiên giúp thư giãn cơ thể và tinh thần."
    },
    {
        "ma_dv": "DV06",
        "ten_dich_vu": "Deep Tissue Therapy at Charm Spa Massage Da Nang",
        "loai_dich_vu": "Massage chuyên sâu",
        "thoi_luong": 90,
        "suc_chua_toi_da": 30,
        "diem_tich_luy_dich_vu": 105,
        "gia_dich_vu": 1050000,
        "mo_ta": "Massage tác động sâu vào lớp cơ và mô liên kết giúp giảm căng cơ cứng đầu."
    },
    {
        "ma_dv": "DV07",
        "ten_dich_vu": "Thai Therapy at Charm Spa Massage Da Nang",
        "loai_dich_vu": "Massage Thái",
        "thoi_luong": 90,
        "suc_chua_toi_da": 30,
        "diem_tich_luy_dich_vu": 100,
        "gia_dich_vu": 1000000,
        "mo_ta": "Massage phong cách Thái kết hợp các động tác kéo giãn linh hoạt."
    },
    {
        "ma_dv": "DV08",
        "ten_dich_vu": "Charm Spa Massage Signature Bamboo Cane",
        "loai_dich_vu": "Massage đặc biệt",
        "thoi_luong": 90,
        "suc_chua_toi_da": 30,
        "diem_tich_luy_dich_vu": 110,
        "gia_dich_vu": 1100000,
        "mo_ta": "Liệu pháp độc quyền sử dụng thanh tre ấm lăn dọc cơ thể mang lại cảm giác cực kỳ thư giãn."
    },
    {
        "ma_dv": "DV09",
        "ten_dich_vu": "Aromatherapy Massage at Charm Spa Massage Da Nang",
        "loai_dich_vu": "Massage tinh dầu",
        "thoi_luong": 90,
        "suc_chua_toi_da": 30,
        "diem_tich_luy_dich_vu": 85,
        "gia_dich_vu": 850000,
        "mo_ta": "Kết hợp kỹ thuật massage nhẹ nhàng với tinh dầu thiên nhiên cao cấp."
    },
    {
        "ma_dv": "DV10",
        "ten_dich_vu": "Swedish Therapy at Charm Spa Da Nang",
        "loai_dich_vu": "Massage Thụy Điển",
        "thoi_luong": 90,
        "suc_chua_toi_da": 30,
        "diem_tich_luy_dich_vu": 85,
        "gia_dich_vu": 850000,
        "mo_ta": "Kỹ thuật massage Thụy Điển kinh điển giúp xua tan căng thẳng mệt mỏi."
    },
    {
        "ma_dv": "DV11",
        "ten_dich_vu": "Body Part Therapy at Charm Spa Massage Đà Nẵng",
        "loai_dich_vu": "Massage bộ phận",
        "thoi_luong": 60,
        "suc_chua_toi_da": 30,
        "diem_tich_luy_dich_vu": 60,
        "gia_dich_vu": 600000,
        "mo_ta": "Tập trung trị liệu chuyên sâu vào các vùng cụ thể như vai, gáy, lưng hoặc chân."
    },
    {
        "ma_dv": "DV12",
        "ten_dich_vu": "Body Relaxation – Body Massage Treatment at Charm Spa",
        "loai_dich_vu": "Thư giãn toàn thân",
        "thoi_luong": 90,
        "suc_chua_toi_da": 30,
        "diem_tich_luy_dich_vu": 90,
        "gia_dich_vu": 900000,
        "mo_ta": "Liệu trình thư giãn toàn thân giúp cân bằng năng lượng và tái tạo sức sống."
    },
    {
        "ma_dv": "DV13",
        "ten_dich_vu": "Foot Reflexology Therapy at Charm Spa Massage Da Nang",
        "loai_dich_vu": "Massage chân",
        "thoi_luong": 60,
        "suc_chua_toi_da": 30,
        "diem_tich_luy_dich_vu": 50,
        "gia_dich_vu": 500000,
        "mo_ta": "Massage bấm huyệt lòng bàn chân kích thích các dây thần kinh thư giãn."
    },
    {
        "ma_dv": "DV14",
        "ten_dich_vu": "Facial Treatment at Charm Spa Massage Da Nang",
        "loai_dich_vu": "Chăm sóc da mặt",
        "thoi_luong": 60,
        "suc_chua_toi_da": 30,
        "diem_tich_luy_dich_vu": 70,
        "gia_dich_vu": 700000,
        "mo_ta": "Chăm sóc và nuôi dưỡng làn da mặt chuyên sâu rạng rỡ tươi trẻ."
    },
    {
        "ma_dv": "DV15",
        "ten_dich_vu": "Body Treatment at Charm Spa Massage Da Nang",
        "loai_dich_vu": "Tẩy tế bào chết/Ủ dưỡng",
        "thoi_luong": 60,
        "suc_chua_toi_da": 30,
        "diem_tich_luy_dich_vu": 80,
        "gia_dich_vu": 800000,
        "mo_ta": "Tẩy tế bào chết và ủ dưỡng toàn thân giúp da mịn màng, trắng sáng."
    },
    {
        "ma_dv": "DV16",
        "ten_dich_vu": "Packages at Charm Spa Massage Da Nang",
        "loai_dich_vu": "Combo trọn gói",
        "thoi_luong": 180,
        "suc_chua_toi_da": 30,
        "diem_tich_luy_dich_vu": 180,
        "gia_dich_vu": 1800000,
        "mo_ta": "Gói combo dịch vụ kết hợp toàn diện (Massage + Chăm sóc da + Gội đầu) ưu đãi đặc biệt."
    },
]

for dv in danh_sach_con_lai:
    DichVu.objects.update_or_create(
        ma_dv=dv["ma_dv"],
        defaults=dv
    )

print("Đã nạp thành công 12 dịch vụ còn lại vào hệ thống tổng cộng đủ 16 dịch vụ!")