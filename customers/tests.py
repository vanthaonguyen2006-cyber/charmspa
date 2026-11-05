from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from customers.models import HangThanhVien, KhachHang


class StaffCustomerAddViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            username='customer_add_staff',
            password='test-password',
            is_staff=True,
        )
        self.client.force_login(self.staff)

        self.lowest_tier = HangThanhVien.objects.create(
            ma_tv='TIER_LOW',
            ten_hang='Hạng khởi điểm',
            diem_toi_thieu=0,
            ty_le_giam_gia=0,
        )
        self.higher_tier = HangThanhVien.objects.create(
            ma_tv='TIER_HIGH',
            ten_hang='Hạng cao hơn',
            diem_toi_thieu=500,
            ty_le_giam_gia=5,
        )

    def test_new_customer_gets_lowest_database_tier_and_zero_points(self):
        response = self.client.post(
            reverse('staff_customer_add'),
            {
                'ho_ten': 'Khách kiểm tra',
                'so_dien_thoai': '0900000001',
                'email': 'customer-test@example.com',
                'gioi_tinh': 'Nữ',
                # Untrusted form data must not override the database selection.
                'ma_tv': self.higher_tier.ma_tv,
            },
        )

        self.assertRedirects(response, reverse('staff_customer_list'))
        customer = KhachHang.objects.get(ho_ten='Khách kiểm tra')
        self.assertEqual(customer.ma_tv, self.lowest_tier)
        self.assertEqual(customer.diem_tich_luy_kh, 0)
        self.assertEqual(customer.ma_tk.so_dien_thoai, '0900000001')
