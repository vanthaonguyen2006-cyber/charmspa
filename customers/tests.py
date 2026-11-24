from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from accounts.models import ROLE_MANAGER, ROLE_STAFF, NhanVien, TaiKhoan
from customers.models import HangThanhVien, KhachHang


class StaffCustomerAddViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            username='customer_add_staff',
            password='test-password',
        )
        TaiKhoan.objects.create(
            ma_tk=f'TK{self.staff.id:03d}',
            user=self.staff,
            so_dien_thoai=f'NV_{self.staff.id:06d}',
            vai_tro=ROLE_STAFF,
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
                'username': 'khach_kiem_tra',
                'password1': 'CharmCustomer2026!',
                'password2': 'CharmCustomer2026!',
                # Untrusted form data must not override the database selection.
                'ma_tv': self.higher_tier.ma_tv,
            },
        )

        self.assertRedirects(response, reverse('staff_customer_list'))
        customer = KhachHang.objects.get(ho_ten='Khách kiểm tra')
        self.assertEqual(customer.ma_tv, self.lowest_tier)
        self.assertEqual(customer.diem_tich_luy_kh, 0)
        self.assertEqual(customer.ma_tk.so_dien_thoai, '0900000001')

        user = customer.ma_tk.user
        self.assertEqual(user.username, 'khach_kiem_tra')
        self.assertEqual(user.email, 'customer-test@example.com')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password('CharmCustomer2026!'))

    def test_customer_add_rejects_weak_and_mismatched_password(self):
        user_model = get_user_model()

        weak_response = self.client.post(
            reverse('staff_customer_add'),
            {
                'ho_ten': 'Khách mật khẩu yếu',
                'so_dien_thoai': '0900000002',
                'email': '',
                'gioi_tinh': 'Nam',
                'username': 'khach_weak_pw',
                'password1': '123456',
                'password2': '123456',
            },
        )
        self.assertEqual(weak_response.status_code, 200)
        self.assertIn('password2', weak_response.context['form'].errors)
        self.assertFalse(user_model.objects.filter(username='khach_weak_pw').exists())
        self.assertFalse(KhachHang.objects.filter(ho_ten='Khách mật khẩu yếu').exists())

        mismatch_response = self.client.post(
            reverse('staff_customer_add'),
            {
                'ho_ten': 'Khách lệch mật khẩu',
                'so_dien_thoai': '0900000003',
                'email': '',
                'gioi_tinh': 'Nam',
                'username': 'khach_mismatch_pw',
                'password1': 'CharmCustomer2026!',
                'password2': 'OtherPass2026!',
            },
        )
        self.assertEqual(mismatch_response.status_code, 200)
        self.assertIn(
            'Mật khẩu xác nhận không khớp.',
            mismatch_response.context['form'].errors.get('password2', []),
        )
        self.assertFalse(user_model.objects.filter(username='khach_mismatch_pw').exists())


class StaffAccountAddStaffViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.manager = user_model.objects.create_user(
            username='manager_add_staff',
            password='ManagerPass123!',
        )
        TaiKhoan.objects.create(
            ma_tk=f'TK{self.manager.id:03d}',
            user=self.manager,
            so_dien_thoai=f'NV_{self.manager.id:06d}',
            vai_tro=ROLE_MANAGER,
        )
        self.client.force_login(self.manager)

    def test_manager_can_create_staff_account_using_user_creation_form(self):
        response = self.client.post(
            reverse('staff_account_add_staff'),
            {
                'ho_ten': 'Nguyễn Văn A',
                'gioi_tinh': 'Nam',
                'so_dien_thoai': '0912345678',
                'email': 'NhanVienA@example.com',
                'ngay_sinh': '',
                'vai_tro': ROLE_STAFF,
                'username': 'nhanvien_moi',
                'password1': 'CharmSpa2026!',
                'password2': 'CharmSpa2026!',
            },
        )

        self.assertRedirects(response, reverse('staff_account_list'))
        messages_list = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(
            any("Đã thêm mới nhân sự 'Nguyễn Văn A' (Nhân viên) thành công!" in msg for msg in messages_list)
        )

        user_model = get_user_model()
        created_user = user_model.objects.get(username='nhanvien_moi')
        self.assertEqual(created_user.email, 'nhanviena@example.com')
        self.assertTrue(created_user.is_active)
        self.assertFalse(created_user.is_staff)
        self.assertFalse(created_user.is_superuser)
        self.assertTrue(created_user.check_password('CharmSpa2026!'))

        tai_khoan = TaiKhoan.objects.get(user=created_user)
        self.assertEqual(tai_khoan.vai_tro, ROLE_STAFF)
        self.assertEqual(tai_khoan.so_dien_thoai, '0912345678')

        nhan_vien = NhanVien.objects.get(ma_tk=tai_khoan)
        self.assertEqual(nhan_vien.ma_nv, f'NV{created_user.id:03d}')
        self.assertEqual(nhan_vien.ho_ten, 'Nguyễn Văn A')
        self.assertEqual(nhan_vien.gioi_tinh, 'Nam')
        self.assertEqual(nhan_vien.ngay_sinh, date(2000, 1, 1))

    def test_rejects_weak_and_mismatched_password_via_user_creation_form(self):
        user_model = get_user_model()

        # Weak password (< 8 characters) should fail Django AUTH_PASSWORD_VALIDATORS on password2
        weak_response = self.client.post(
            reverse('staff_account_add_staff'),
            {
                'ho_ten': 'Trần Thị B',
                'gioi_tinh': 'Nữ',
                'so_dien_thoai': '0987654321',
                'email': 'nhanvienb@example.com',
                'ngay_sinh': '1999-05-15',
                'vai_tro': ROLE_STAFF,
                'username': 'nhanvien_weak',
                'password1': '123456',
                'password2': '123456',
            },
        )
        self.assertEqual(weak_response.status_code, 200)
        self.assertIn('password2', weak_response.context['form'].errors)
        self.assertFalse(user_model.objects.filter(username='nhanvien_weak').exists())

        # Mismatched password2 should fail with Vietnamese password_mismatch message
        mismatch_response = self.client.post(
            reverse('staff_account_add_staff'),
            {
                'ho_ten': 'Trần Thị B',
                'gioi_tinh': 'Nữ',
                'so_dien_thoai': '0987654321',
                'email': 'nhanvienb@example.com',
                'ngay_sinh': '1999-05-15',
                'vai_tro': ROLE_STAFF,
                'username': 'nhanvien_mismatch',
                'password1': 'CharmSpa2026!',
                'password2': 'DifferentPass99!',
            },
        )
        self.assertEqual(mismatch_response.status_code, 200)
        form = mismatch_response.context['form']
        self.assertIn('Mật khẩu xác nhận không khớp.', form.errors.get('password2', []))
        self.assertFalse(user_model.objects.filter(username='nhanvien_mismatch').exists())
