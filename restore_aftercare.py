
# -*- coding: utf-8 -*-
"""
Khoi phuc mau huong dan cham soc tu database backup.
Chi them mau CHUA TON TAI, khong ghi de mau cua nhom.
"""

import sqlite3
from pathlib import Path

from django.db import transaction
from notifications.models import HuongDanChamSoc
from services.models import DichVu

# LUON XEM THU TRUOC
DRY_RUN = False

BACKUP_DB = Path(
    r"D:\python\charmspa_backup_20261118\db.sqlite3"
)

if not BACKUP_DB.is_file():
    raise FileNotFoundError(f"Khong tim thay: {BACKUP_DB}")

table = HuongDanChamSoc._meta.db_table
pk_field = HuongDanChamSoc._meta.pk.attname

# Doc database cu, khong ghi
uri = BACKUP_DB.resolve().as_uri() + "?mode=ro"
conn = sqlite3.connect(uri, uri=True)
conn.row_factory = sqlite3.Row

try:
    rows = [
        dict(row)
        for row in conn.execute(
            f'SELECT * FROM "{table}"'
        ).fetchall()
    ]
finally:
    conn.close()

# Chi khoi phuc bo 16 mau cua minh
rows = [
    r for r in rows
    if str(r[pk_field]) in {
        f"HD260{i:03d}" for i in range(1, 17)
    }
]

if not rows:
    raise ValueError(
        "Khong tim thay 16 mau HDCS trong database backup."
    )

# Doi chieu cau truc model
fields = {
    field.attname
    for field in HuongDanChamSoc._meta.concrete_fields
}

source_fields = set(rows[0])

if source_fields != fields:
    raise ValueError(
        f"Cau truc khac nhau!\n"
        f"Chi co trong backup: {source_fields - fields}\n"
        f"Chi co trong model moi: {fields - source_fields}"
    )

# Kiem tra ma mau bi trung
codes = [r[pk_field] for r in rows]

if len(codes) != len(set(codes)):
    raise ValueError("Database backup co ma mau trung nhau.")

# Kiem tra lien ket dich vu
service_ids = {
    r["ma_dv_id"]
    for r in rows
    if r.get("ma_dv_id")
}

valid_ids = set(
    DichVu.objects.filter(
        pk__in=service_ids
    ).values_list("pk", flat=True)
)

missing_services = service_ids - valid_ids

if missing_services:
    raise ValueError(
        f"Ma dich vu khong ton tai: {sorted(missing_services)}"
    )

# Kiem tra mau da ton tai
existing = set(
    HuongDanChamSoc.objects.filter(
        pk__in=codes
    ).values_list("pk", flat=True)
)

new_rows = [
    r for r in rows
    if r[pk_field] not in existing
]

print("=" * 65)
print("KHOI PHUC HUONG DAN CHAM SOC")
print("CHE DO:", "XEM THU" if DRY_RUN else "GHI DATABASE")
print("SO MAU TRONG BACKUP:", len(rows))
print("DA TON TAI:", len(existing))
print("SE KHOI PHUC:", len(new_rows))
print("=" * 65)

for row in rows:
    code = row[pk_field]
    status = (
        "GIU NGUYEN"
        if code in existing
        else "KHOI PHUC"
    )

    print(
        f"{status} | "
        f"{code} | "
        f"{row.get('ma_dv_id')} | "
        f"{row.get('tieu_de')} | "
        f"{row.get('trang_thai')}"
    )

if DRY_RUN:
    print("\nCHUA GHI DU LIEU.")
    print("Xem ket qua truoc khi doi DRY_RUN = False.")
else:
    with transaction.atomic():
        for row in new_rows:
            HuongDanChamSoc.objects.create(**row)

    print("\nKHOI PHUC HOAN TAT!")
    print("SO MAU DA THEM:", len(new_rows))
    print(
        "TONG SO MAU HIEN TAI:",
        HuongDanChamSoc.objects.count()
    )
