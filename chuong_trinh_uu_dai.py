# -*- coding: utf-8 -*-
"""Update ONLY hinh_anh URL for the 10 demo promotions.

1. Replace empty strings in IMAGE_URLS with publicly accessible HTTPS image URLs.
2. Set DRY_RUN = False after reviewing preview.
3. From folder with manage.py run in PowerShell:
   python manage.py shell -c "exec(compile(open('update_charm_promotion_image_urls.py', encoding='utf-8').read(), 'update_charm_promotion_image_urls.py', 'exec'))"

Does not alter titles, descriptions, prices, statuses, services or dates.
"""
from urllib.parse import urlsplit
from django.db import transaction
from notifications.models import ChuongTrinhUuDai

DRY_RUN = True

# Paste the REAL public image URL between quotes. Leave empty to SKIP a program.
IMAGE_URLS = {
    'DM260001': 'https://images.pexels.com/photos/19666192/pexels-photo-19666192.jpeg',
    'DM260002': 'https://images.pexels.com/photos/6560279/pexels-photo-6560279.jpeg',
    'DM260003': 'https://images.pexels.com/photos/7239303/pexels-photo-7239303.jpeg',
    'DM260004': 'https://images.pexels.com/photos/6187430/pexels-photo-6187430.jpeg',
    'DM260005': 'https://images.pexels.com/photos/31914703/pexels-photo-31914703.jpeg',
    'DM260006': 'https://images.pexels.com/photos/4599388/pexels-photo-4599388.jpeg',
    'DM260007': 'https://images.pexels.com/photos/6663373/pexels-photo-6663373.jpeg',
    'DM260008': 'https://images.pexels.com/photos/7795646/pexels-photo-7795646.jpeg',
    'DM260009': 'https://images.pexels.com/photos/11774389/pexels-photo-11774389.jpeg',
    'DM260010': 'https://images.pexels.com/photos/23349902/pexels-photo-23349902.jpeg',
}

EXPECTED_SERVICE = {
    'DM260001': 'DV09', 'DM260002': 'DV04', 'DM260003': 'DV05',
    'DM260004': 'DV06', 'DM260005': 'DV10', 'DM260006': 'DV13',
    'DM260007': 'DV14', 'DM260008': 'DV15', 'DM260009': 'DV16',
    'DM260010': 'DV01',
}

updates = {}
for code, raw in IMAGE_URLS.items():
    url = raw.strip()
    if not url:
        continue
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.netloc:
        raise ValueError(f'{code}: URL phải bắt đầu bằng https:// hoặc http:// và có tên miền.')
    if len(url) > 500 or any(c.isspace() for c in url):
        raise ValueError(f'{code}: URL dài quá 500 ký tự hoặc chứa khoảng trắng.')
    updates[code] = url

if not updates:
    raise ValueError('Chưa dán URL ảnh nào. Mở IMAGE_URLS và nhập ít nhất một URL thật.')

promos = {p.pk: p for p in ChuongTrinhUuDai.objects.filter(pk__in=updates)}
missing = sorted(set(updates) - set(promos))
if missing:
    raise ValueError('Không tìm thấy chương trình: ' + ', '.join(missing))
for code, promo in promos.items():
    if promo.ma_dv_id != EXPECTED_SERVICE[code]:
        raise ValueError(f'{code}: Mã dịch vụ hiện tại không khớp; đã dừng, chưa cập nhật gì.')

print('CHẾ ĐỘ:', 'XEM THỬ' if DRY_RUN else 'GHI VÀO DATABASE')
for code, url in updates.items():
    print(f'{code} | {promos[code].ten_chuong_trinh} | {url}')

if DRY_RUN:
    print('CHƯA CẬP NHẬT. Đổi DRY_RUN = False và chạy lại để lưu URL.')
else:
    with transaction.atomic():
        for code, url in updates.items():
            promo = promos[code]
            promo.hinh_anh = url
            promo.save(update_fields=['hinh_anh'])
    print(f'ĐÃ CẬP NHẬT {len(updates)} URL ảnh. Các trường khác được giữ nguyên.')
