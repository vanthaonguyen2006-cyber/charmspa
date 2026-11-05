from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

class AccountChangePasswordViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='password_change_customer',
            email='password-customer@example.com',
            password='OldValidPassword!2024',
        )
        self.client.force_login(self.user)

    def test_password_change_keeps_customer_logged_in(self):
        response = self.client.post(
            reverse('account_change_password'),
            {
                'old_password': 'OldValidPassword!2024',
                'new_password1': 'NewSecureSpaPassword!2026',
                'new_password2': 'NewSecureSpaPassword!2026',
            },
            follow=True,
        )

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecureSpaPassword!2026'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertContains(response, 'đã được đổi thành công')

    def test_wrong_current_password_shows_error_without_changing_password(self):
        response = self.client.post(
            reverse('account_change_password'),
            {
                'old_password': 'incorrect-current-password',
                'new_password1': 'NewSecureSpaPassword!2026',
                'new_password2': 'NewSecureSpaPassword!2026',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('old_password', response.context['form'].errors)
        self.assertTrue(self.user.check_password('OldValidPassword!2024'))

    def test_mismatched_and_weak_new_passwords_are_rejected(self):
        mismatch_response = self.client.post(
            reverse('account_change_password'),
            {
                'old_password': 'OldValidPassword!2024',
                'new_password1': 'NewSecureSpaPassword!2026',
                'new_password2': 'DifferentSecurePassword!2026',
            },
        )
        self.assertIn('new_password2', mismatch_response.context['form'].errors)

        weak_response = self.client.post(
            reverse('account_change_password'),
            {
                'old_password': 'OldValidPassword!2024',
                'new_password1': 'password',
                'new_password2': 'password',
            },
        )
        self.assertIn('new_password2', weak_response.context['form'].errors)
        self.assertTrue(self.user.check_password('OldValidPassword!2024'))


class StaffChangePasswordViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='staff_password_change',
            password='OldStaffPassword!2024',
            is_staff=True,
        )
        self.client.force_login(self.user)

    def test_staff_can_change_password_from_staff_layout_and_stay_logged_in(self):
        response = self.client.post(
            reverse('staff_change_password'),
            {
                'old_password': 'OldStaffPassword!2024',
                'new_password1': 'NewStaffSecurePassword!2026',
                'new_password2': 'NewStaffSecurePassword!2026',
            },
            follow=True,
        )

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewStaffSecurePassword!2026'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertContains(response, 'Bảo mật tài khoản')
        self.assertContains(response, 'Đổi mật khẩu')
