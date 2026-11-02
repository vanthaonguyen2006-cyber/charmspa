# Migration điều chỉnh các model phản hồi và khiếu nại
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    # Các migration cần hoàn tất trước khi chạy migration này
    dependencies = [
        ('customers', '0001_initial'),
        ('services', '0001_initial'),
        ('accounts', '0001_initial'),
        ('feedback', '0001_initial'),
    ]

    operations = [
        # Cấu hình thứ tự hiển thị lịch sử xử lý
        migrations.AlterModelOptions(
            name='lichsuxuly',
            options={'ordering': ['ngay_thuc_hien']},
        ),

        # Đã bỏ 3 AddField vì các cột có thể đã tồn tại trong 0001_initial:
        # - PhanCongXuLy.thoi_gian_ket_thuc
        # - PhanHoiKhieuNai.chi_tiet_ly_do
        # - PhanHoiKhieuNai.ngay_cap_nhat

        # Cập nhật loại thao tác trong lịch sử xử lý
        migrations.AlterField(
            model_name='lichsuxuly',
            name='loai_thao_tac',
            field=models.CharField(
                choices=[
                    ('Phân công', 'Phân công'),
                    ('Cập nhật trạng thái', 'Cập nhật trạng thái'),
                    ('Cập nhật xử lý', 'Cập nhật xử lý'),
                    ('Đánh dấu không hợp lệ', 'Đánh dấu không hợp lệ'),
                    ('Hoàn tất xử lý', 'Hoàn tất xử lý'),
                ],
                max_length=50,
                verbose_name='Loại thao tác',
            ),
        ),

        # Cập nhật liên kết người thực hiện trong lịch sử
        migrations.AlterField(
            model_name='lichsuxuly',
            name='ma_nguoi_thuc_hien',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='lich_su_da_thuc_hien',
                to='accounts.taikhoan',
                verbose_name='Người thực hiện',
            ),
        ),

        # Cập nhật liên kết phiếu phản hồi trong lịch sử
        migrations.AlterField(
            model_name='lichsuxuly',
            name='ma_ph',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='lich_su_xu_ly',
                to='feedback.phanhoikhieunai',
                verbose_name='Phiếu phản hồi',
            ),
        ),

        # Cập nhật liên kết tài khoản admin thực hiện phân công
        migrations.AlterField(
            model_name='phancongxuly',
            name='ma_nguoi_phan_cong',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='phan_cong_da_thuc_hien',
                to='accounts.taikhoan',
                verbose_name='Quản trị viên phân công',
            ),
        ),

        # Cập nhật liên kết nhân viên phụ trách phiếu
        migrations.AlterField(
            model_name='phancongxuly',
            name='ma_nv',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='phan_cong_xu_ly',
                to='accounts.nhanvien',
                verbose_name='Nhân viên xử lý',
            ),
        ),

        # Cập nhật liên kết phiếu trong bảng phân công
        migrations.AlterField(
            model_name='phancongxuly',
            name='ma_ph',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='phan_cong',
                to='feedback.phanhoikhieunai',
                verbose_name='Phiếu phản hồi',
            ),
        ),

        # Cập nhật danh sách lý do không hợp lệ
        migrations.AlterField(
            model_name='phanhoikhieunai',
            name='ly_do_khong_hop_le',
            field=models.CharField(
                blank=True,
                choices=[
                    ('Gửi nhầm', 'Gửi nhầm'),
                    ('Trùng lặp', 'Trùng lặp'),
                    ('Spam', 'Spam'),
                    ('Nội dung không liên quan', 'Nội dung không liên quan'),
                    ('Khác', 'Khác'),
                ],
                max_length=255,
                null=True,
                verbose_name='Lý do không hợp lệ',
            ),
        ),

        # Cập nhật liên kết dịch vụ của phiếu phản hồi
        migrations.AlterField(
            model_name='phanhoikhieunai',
            name='ma_dv',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='phan_hoi_khieu_nai',
                to='services.dichvu',
                verbose_name='Dịch vụ liên quan',
            ),
        ),

        # Cập nhật liên kết khách hàng của phiếu phản hồi
        migrations.AlterField(
            model_name='phanhoikhieunai',
            name='ma_kh',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='phan_hoi_khieu_nai',
                to='customers.khachhang',
                verbose_name='Khách hàng',
            ),
        ),

        # Cập nhật trường đánh giá tính hợp lệ
        migrations.AlterField(
            model_name='phanhoikhieunai',
            name='tinh_hop_le',
            field=models.CharField(
                choices=[
                    ('Hợp lệ', 'Hợp lệ'),
                    ('Không hợp lệ', 'Không hợp lệ'),
                ],
                default='Hợp lệ',
                max_length=20,
                verbose_name='Tính hợp lệ',
            ),
        ),

        # Cập nhật các trạng thái xử lý phiếu
        migrations.AlterField(
            model_name='phanhoikhieunai',
            name='trang_thai_xu_ly',
            field=models.CharField(
                choices=[
                    ('Đã tiếp nhận', 'Đã tiếp nhận'),
                    ('Đang xử lý', 'Đang xử lý'),
                    ('Đã giải quyết', 'Đã giải quyết'),
                ],
                default='Đã tiếp nhận',
                max_length=20,
                verbose_name='Trạng thái xử lý',
            ),
        ),

        # Cập nhật liên kết phiếu trong bảng tệp đính kèm
        migrations.AlterField(
            model_name='tepdinhkem',
            name='ma_ph',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tep_dinh_kem',
                to='feedback.phanhoikhieunai',
                verbose_name='Phiếu phản hồi',
            ),
        ),

        # Đặt tên bảng lịch sử xử lý theo cấu hình model
        migrations.AlterModelTable(
            name='lichsuxuly',
            table='LICH_SU_XU_LY',
        ),

        # Đặt tên bảng phân công xử lý theo cấu hình model
        migrations.AlterModelTable(
            name='phancongxuly',
            table='PHAN_CONG_XU_LY',
        ),

        # Đặt tên bảng phản hồi và khiếu nại theo cấu hình model
        migrations.AlterModelTable(
            name='phanhoikhieunai',
            table='PHAN_HOI_KHIEU_NAI',
        ),

        # Đặt tên bảng tệp đính kèm theo cấu hình model
        migrations.AlterModelTable(
            name='tepdinhkem',
            table='TEP_DINH_KEM',
        ),
    ]