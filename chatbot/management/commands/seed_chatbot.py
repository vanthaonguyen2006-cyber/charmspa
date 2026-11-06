"""
Khôi phục / tạo kịch bản chatbot.

  python manage.py seed_chatbot --from-backup db.sqlite3.bak   # lấy lại kịch bản từ DB cũ
  python manage.py seed_chatbot                                # tạo kịch bản mẫu KB001 (giống báo cáo) nếu chưa có
  python manage.py seed_chatbot --reset                        # ghi đè sơ đồ KB001 bằng sơ đồ mẫu
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from chatbot import flow_utils
from chatbot.models import KichBanChatbot


class Command(BaseCommand):
    help = 'Khôi phục kịch bản chatbot từ DB cũ hoặc tạo kịch bản mẫu.'

    def add_arguments(self, parser):
        parser.add_argument('--from-backup', metavar='FILE',
                            help='Chép kịch bản từ file SQLite cũ (ví dụ db.sqlite3.bak).')
        parser.add_argument('--reset', action='store_true',
                            help='Ghi đè sơ đồ của kịch bản KB001 bằng sơ đồ mẫu.')

    def handle(self, *args, **options):
        if options.get('from_backup'):
            self._restore(options['from_backup'])
        else:
            self._seed(options['reset'])

    def _restore(self, backup):
        db = settings.DATABASES['default']
        if 'sqlite' not in db['ENGINE']:
            raise CommandError('Lệnh này chỉ dùng cho cơ sở dữ liệu SQLite.')
        old_path = Path(backup)
        if not old_path.is_absolute():
            old_path = Path(settings.BASE_DIR) / old_path
        if not old_path.is_file():
            raise CommandError(f'Không tìm thấy file: {old_path}')

        result = flow_utils.restore_scripts_from_sqlite(db['NAME'], old_path)
        labels = {'chatbot_kichbanchatbot': 'Kịch bản', 'chatbot_buocchatbot': 'Các bước',
                  'chatbot_sodokichban': 'Sơ đồ kéo thả'}
        for table, count in result.items():
            text = 'không có bảng này ở DB cũ hoặc DB mới' if count is None else f'đã chép {count} dòng'
            self.stdout.write(f'  {labels[table]}: {text}')
        if not any(result.values()):
            self.stdout.write(self.style.WARNING(
                'Không chép được kịch bản nào. Chạy "python manage.py seed_chatbot" để tạo kịch bản mẫu.'))
        else:
            self.stdout.write(self.style.SUCCESS('Đã khôi phục kịch bản. Mở trang Quản lý kịch bản để kiểm tra.'))

    def _seed(self, reset):
        name = 'Tư vấn dịch vụ'
        if KichBanChatbot.objects.filter(ten_kich_ban=name).exclude(pk='KB001').exists():
            name += ' (mẫu)'
        with transaction.atomic():
            script, created = KichBanChatbot.objects.get_or_create(
                ma_kb='KB001',
                defaults={
                    'ten_kich_ban': name,
                    'mo_ta': 'Giới thiệu nhóm dịch vụ, thông tin giá và hỗ trợ tư vấn riêng tại Charm Grand Spa Đà Nẵng.',
                    'trang_thai': 'Đang hoạt động',
                })
            has_graph = hasattr(script, 'so_do')
            if created or reset or not has_graph:
                flow_utils.save_graph(script, flow_utils.sanitize_graph(flow_utils.build_default_graph()))
                self.stdout.write(self.style.SUCCESS('Đã tạo kịch bản mẫu KB001 với sơ đồ giống báo cáo.'))
            else:
                self.stdout.write('Kịch bản KB001 đã có sơ đồ, không thay đổi. Dùng --reset nếu muốn ghi đè.')
