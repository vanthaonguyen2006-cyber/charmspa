
# -*- coding: utf-8 -*-
"""
Khoi phuc chuong trinh uu dai tu database backup.
Chay trong thu muc chua manage.py:

python manage.py shell -c "exec(compile(open('restore_promotions.py', encoding='utf-8').read(), 'restore_promotions.py', 'exec'))"
"""

import sqlite3
from pathlib import Path
from django.db import transaction
from services.models import DichVu
from notifications.models import ChuongTrinhUuDai

DRY_RUN = True

BACKUP_DB = Path(
    r"D:\python\charmspa_backup_20261118\db.sqlite3"
)

TABLE = "notifications_chuongtrinhuudai"

if not BACKUP_DB.exists():
    raise FileNotFoundError(
        f"Khong tim thay database backup: {BACKUP_DB}"
    )

# 1. Doc database backup
connection = sqlite3.connect(
    BACKUP_DB.as_uri() + "?mode=ro",
    uri=True
)
connection.row_factory = sqlite3.Row

try:
    rows = [
        dict(row)
        for row in connection.execute(
            f'SELECT * FROM "{TABLE}"'
        ).fetchall()
    ]
finally:
    connection.close()

print("=" * 60)
print("CHE DO:", "XEM THU" if DRY_RUN else "KHOI PHUC")
print("SO UU DAI TRONG BACKUP:", len(rows))
print("=" * 60)

# 2. Kiem tra cac truong va ma dich vu
model_fields = {
    f.attname: f
    for f in ChuongTrinhUuDai._meta.concrete_fields
}

source_columns = set(rows[0].keys()) if rows else set()
target_columns = set(model_fields)

unknown_columns = source_columns - target_columns
missing_columns = target_columns - source_columns

if unknown_columns or missing_columns:
    raise ValueError(
        f"Cau truc khong khop. "
        f"Truong thua: {unknown_columns}. "
        f"Truong thieu: {missing_columns}"
    )

source_ids = [row["ma_ctud"] for row in rows]

if len(source_ids) != len(set(source_ids)):
    raise ValueError("Database backup co ma uu dai trung nhau.")

existing_ids = set(
    ChuongTrinhUuDai.objects.filter(
        pk__in=source_ids
    ).values_list("pk", flat=True)
)

service_ids = {
    row["ma_dv_id"]
    for row in rows
    if row["ma_dv_id"]
}

valid_services = set(
    DichVu.objects.filter(
        pk__in=service_ids
    ).values_list("pk", flat=True)
)

missing_services = service_ids - valid_services

if missing_services:
    raise ValueError(
        "Thieu ma dich vu: " + ", ".join(sorted(missing_services))
    )

new_rows = [
    row for row in rows
    if row["ma_ctud"] not in existing_ids
]

print("SO UU DAI DA TON TAI:", len(existing_ids))
print("SO UU DAI SE KHOI PHUC:", len(new_rows))

for row in rows:
    status = (
        "BO QUA - DA TON TAI"
        if row["ma_ctud"] in existing_ids
        else "KHOI PHUC"
    )

    print(
        f"{status} | "
        f"{row['ma_ctud']} | "
        f"{row['ten_chuong_trinh']} | "
        f"{row['ma_dv_id']}"
    )

# 3. Thuc hien neu duoc cho phep
if DRY_RUN:
    print("\nCHUA GHI DU LIEU.")
    print("Kiem tra danh sach truoc khi doi DRY_RUN = False.")

else:
    with transaction.atomic():
        for row in new_rows:
            obj = ChuongTrinhUuDai(
                **{
                    key: value
                    for key, value in row.items()
                    if key in model_fields
                }
            )
            obj.save(force_insert=True)

    print("\nKHOI PHUC THANH CONG!")
    print("SO CHUONG TRINH MOI:", len(new_rows))
    print(
        "TONG SO UU DAI:",
        ChuongTrinhUuDai.objects.count()
    )
