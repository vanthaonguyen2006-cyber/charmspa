"""
Tiện ích cho trình dựng kịch bản kéo thả (Flow Builder).

Sơ đồ kịch bản được lưu dạng JSON:
{
  "nodes": [
    {"id": "chao_mung", "type": "tin_nhan", "title": "Chào mừng", "content": "...",
     "x": 140, "y": 160, "ma_buoc": "B1A2B3C4",
     "options": [{"id": "o1", "text": "Xem dịch vụ", "nextId": "xem_dich_vu"}],
     "duration": 90, "price": 1250000, "image_url": ""}
  ]
}
Node có type = "bat_dau" là điểm khởi đầu, options[0].nextId là bước đầu tiên.
"""
import re
import uuid
from collections import deque

ALLOWED_TYPES = {
    'bat_dau', 'tin_nhan', 'hinh_anh', 'dich_vu',
    'form', 'chuyen_nhan_vien', 'chat_truc_tiep',
}
MAX_NODES = 200
MAX_OPTIONS = 20


# --------------------------------------------------------------------------
# Làm sạch dữ liệu nhận từ trình duyệt
# --------------------------------------------------------------------------
def _text(value, limit):
    if value is None:
        return ''
    return str(value).strip()[:limit]


def _num(value, default, lo, hi):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:  # NaN
        return default
    return max(lo, min(hi, number))


def _new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def sanitize_graph(raw):
    """Kiểm tra và chuẩn hóa sơ đồ. Ném ValueError nếu dữ liệu không dùng được."""
    if not isinstance(raw, dict):
        raise ValueError('Dữ liệu sơ đồ không hợp lệ.')
    raw_nodes = raw.get('nodes')
    if not isinstance(raw_nodes, list):
        raise ValueError('Sơ đồ thiếu danh sách bước.')
    if len(raw_nodes) > MAX_NODES:
        raise ValueError(f'Sơ đồ có quá nhiều bước (tối đa {MAX_NODES}).')

    nodes, ids, has_start = [], set(), False
    for rn in raw_nodes:
        if not isinstance(rn, dict):
            continue
        node_id = _text(rn.get('id'), 40)
        node_type = rn.get('type')
        if not node_id or node_id in ids or node_type not in ALLOWED_TYPES:
            continue
        if node_type == 'bat_dau':
            if has_start:
                continue
            has_start = True
        ids.add(node_id)

        options = []
        raw_options = rn.get('options') if isinstance(rn.get('options'), list) else []
        for ro in raw_options[:MAX_OPTIONS]:
            if not isinstance(ro, dict):
                continue
            options.append({
                'id': _text(ro.get('id'), 40) or _new_id('o'),
                'text': _text(ro.get('text'), 100),
                'nextId': _text(ro.get('nextId'), 40),
            })

        nodes.append({
            'id': node_id,
            'type': node_type,
            'title': _text(rn.get('title'), 150) or ('Bắt đầu' if node_type == 'bat_dau' else 'Bước mới'),
            'content': _text(rn.get('content'), 1000),
            'x': round(_num(rn.get('x'), 0, -5000, 5000)),
            'y': round(_num(rn.get('y'), 0, -5000, 5000)),
            'ma_buoc': _text(rn.get('ma_buoc'), 10),
            'options': options,
            'duration': int(_num(rn.get('duration'), 0, 0, 100000)),
            'price': int(_num(rn.get('price'), 0, 0, 10 ** 10)),
            'image_url': _text(rn.get('image_url'), 500),
        })

    if not has_start:
        nodes.insert(0, {
            'id': 'start_node', 'type': 'bat_dau', 'title': 'Bắt đầu', 'content': '',
            'x': 20, 'y': 20, 'ma_buoc': '', 'duration': 0, 'price': 0, 'image_url': '',
            'options': [{'id': _new_id('o'), 'text': '', 'nextId': ''}],
        })
        ids.add('start_node')

    for node in nodes:
        if node['type'] == 'bat_dau':
            first = node['options'][0] if node['options'] else {'id': _new_id('o'), 'text': '', 'nextId': ''}
            node['options'] = [first]
        for opt in node['options']:
            if opt['nextId'] not in ids or opt['nextId'] == node['id']:
                opt['nextId'] = ''
        if node['type'] == 'chat_truc_tiep':
            node['options'] = []
    return {'nodes': nodes}


# --------------------------------------------------------------------------
# Sơ đồ mẫu
# --------------------------------------------------------------------------
def _node(node_id, node_type, title, content, x, y, options=None, **extra):
    node = {
        'id': node_id, 'type': node_type, 'title': title, 'content': content,
        'x': x, 'y': y, 'ma_buoc': '', 'duration': 0, 'price': 0, 'image_url': '',
        'options': [],
    }
    node.update(extra)
    # Mã nút cố định theo bước + vị trí: sơ đồ mẫu được dựng lại ở mỗi yêu cầu,
    # nếu mã ngẫu nhiên thì lần bấm nút sẽ không khớp với lần hiển thị nút.
    for index, (text, next_id) in enumerate(options or []):
        node['options'].append({'id': f"{node_id}_o{index}", 'text': text, 'nextId': next_id})
    return node


def build_starter_graph():
    """Sơ đồ tối thiểu cho kịch bản mới: Bắt đầu -> Chào mừng."""
    return {'nodes': [
        _node('start_node', 'bat_dau', 'Bắt đầu', '', 20, 120, [('', 'chao_mung')]),
        _node('chao_mung', 'tin_nhan', 'Chào mừng',
              'Lắng nghe bạn, chăm sóc tận tâm.\nXin chào, bạn muốn tìm hiểu gì?', 140, 80),
    ]}


def build_default_graph():
    """Sơ đồ mẫu giống hình trong báo cáo (kịch bản 'Tư vấn dịch vụ')."""
    return {'nodes': [
        _node('start_node', 'bat_dau', 'Bắt đầu', '', 20, 200, [('', 'chao_mung')]),
        _node('chao_mung', 'tin_nhan', 'Chào mừng',
              'Lắng nghe bạn, chăm sóc tận tâm.\nXin chào, bạn muốn tìm hiểu gì?', 140, 150, [
                  ('Xem dịch vụ', 'xem_dich_vu'), ('Hỏi về giá', 'hoi_gia'),
                  ('Khuyến mãi', 'khuyen_mai'), ('Yêu cầu tư vấn', 'form_tu_van')]),
        _node('xem_dich_vu', 'tin_nhan', 'Xem dịch vụ', 'Bạn muốn khám phá nhóm nào?', 450, 60, [
            ('Massage', 'massage'), ('Chăm sóc da', 'cham_soc_da'), ('Liệu trình cơ thể', 'lieu_trinh')]),
        _node('hoi_gia', 'tin_nhan', 'Hỏi giá', 'Bạn muốn biết giá của nhóm dịch vụ nào?', 450, 300,
              [('Chọn nhóm dịch vụ', 'xem_dich_vu')]),
        _node('khuyen_mai', 'tin_nhan', 'Khuyến mãi',
              'Ưu đãi đang được cập nhật. Nhân viên sẽ tư vấn ưu đãi phù hợp.', 450, 470,
              [('Yêu cầu tư vấn', 'form_tu_van')]),
        _node('massage', 'tin_nhan', 'Massage', 'Khám phá Golden Calm Therapy', 760, 60,
              [('Golden Calm Therapy', 'golden_calm')]),
        _node('cham_soc_da', 'tin_nhan', 'Chăm sóc da', 'Tư vấn theo nhu cầu làn da', 760, 230,
              [('Yêu cầu tư vấn', 'form_tu_van')]),
        _node('lieu_trinh', 'tin_nhan', 'Liệu trình cơ thể', 'Tư vấn chăm sóc cơ thể phù hợp', 760, 400,
              [('Yêu cầu tư vấn', 'form_tu_van')]),
        _node('golden_calm', 'dich_vu', 'Golden Calm Therapy', 'Liệu trình thư giãn toàn thân.',
              1070, 60, [('Yêu cầu tư vấn', 'form_tu_van')], duration=90, price=1250000),
        _node('form_tu_van', 'form', 'Yêu cầu tư vấn', 'Họ tên, Số điện thoại, Nhu cầu tư vấn', 760, 600,
              [('Gửi yêu cầu', 'cho_tiep_nhan')]),
        _node('cho_tiep_nhan', 'chuyen_nhan_vien', 'Chờ tiếp nhận', 'Sau khi gửi form', 1070, 600,
              [('Khi nhân viên tiếp nhận', 'chat_truc_tiep')]),
        _node('chat_truc_tiep', 'chat_truc_tiep', 'Nhân viên tiếp nhận',
              'Nhân viên tư vấn · Đang hỗ trợ. Mở ô nhập tin nhắn.', 1070, 770),
    ]}


# --------------------------------------------------------------------------
# Thứ tự bước + đồng bộ sang bảng BuocChatbot
# --------------------------------------------------------------------------
def bfs_order(graph):
    """Các bước (không gồm 'Bắt đầu') theo thứ tự đi từ Bắt đầu; bước chưa nối xếp cuối."""
    nodes = graph['nodes']
    by_id = {n['id']: n for n in nodes}
    start = next((n for n in nodes if n['type'] == 'bat_dau'), None)
    order, seen = [], set()
    if start:
        seen.add(start['id'])
        queue = deque(o['nextId'] for o in start['options'] if o['nextId'])
        while queue:
            node_id = queue.popleft()
            if node_id in seen or node_id not in by_id:
                continue
            seen.add(node_id)
            order.append(by_id[node_id])
            queue.extend(o['nextId'] for o in by_id[node_id]['options'] if o['nextId'])
    for node in nodes:
        if node['id'] not in seen and node['type'] != 'bat_dau':
            order.append(node)
    return order


def step_text(node):
    text = node.get('content') or ''
    if node['type'] == 'dich_vu':
        extra = f"{node.get('duration') or 0} phút · {node.get('price') or 0:,}đ".replace(',', '.')
        text = f"{text}\n{extra}".strip()
    return text or node.get('title') or ''


def sync_steps(script, graph):
    """Đồng bộ các node sang BuocChatbot để dữ liệu khớp báo cáo. Gán ma_buoc cho node mới."""
    from .models import BuocChatbot

    existing = {b.ma_buoc: b for b in BuocChatbot.objects.filter(ma_kb=script)}
    kept = set()
    for index, node in enumerate(bfs_order(graph), start=1):
        step = existing.get(node.get('ma_buoc')) if node.get('ma_buoc') else None
        if step is None:
            ma_buoc = f"B{uuid.uuid4().hex[:8].upper()}"
            while BuocChatbot.objects.filter(pk=ma_buoc).exists():
                ma_buoc = f"B{uuid.uuid4().hex[:8].upper()}"
            step = BuocChatbot(ma_buoc=ma_buoc, ma_kb=script)
            node['ma_buoc'] = ma_buoc
        step.ten_buoc = node['title']
        step.noi_dung = step_text(node)
        step.thu_tu = index
        step.trang_thai = 'Đang hoạt động'
        step.save()
        kept.add(step.ma_buoc)
    BuocChatbot.objects.filter(ma_kb=script).exclude(ma_buoc__in=kept).delete()
    return graph


def save_graph(script, graph):
    from .models import SoDoKichBan

    graph = sync_steps(script, graph)
    SoDoKichBan.objects.update_or_create(kich_ban=script, defaults={'du_lieu': graph})
    script.save(update_fields=['ngay_cap_nhat'])
    return graph


def load_graph(script):
    from .models import SoDoKichBan

    so_do = SoDoKichBan.objects.filter(kich_ban=script).first()
    if so_do and isinstance(so_do.du_lieu, dict) and so_do.du_lieu.get('nodes'):
        try:
            return sanitize_graph(so_do.du_lieu)
        except ValueError:
            pass
    return build_default_graph()


# --------------------------------------------------------------------------
# Tải ảnh lên cho hộp "Hình ảnh"
# --------------------------------------------------------------------------
IMAGE_MAX_BYTES = 5 * 1024 * 1024
MEDIA_NAME_RE = re.compile(r'^[0-9a-f]{32}\.(jpg|png|gif|webp)$')
IMAGE_CONTENT_TYPES = {'jpg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp'}


def detect_image_ext(head):
    """Nhận dạng định dạng ảnh theo nội dung thật của file (không tin tên file). Trả về None nếu không phải ảnh hợp lệ."""
    if head.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if head.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if head[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        return 'webp'
    return None


# --------------------------------------------------------------------------
# Khôi phục kịch bản từ file SQLite cũ (ví dụ db.sqlite3.bak) - chỉ dùng thư viện chuẩn
# --------------------------------------------------------------------------
RESTORE_TABLES = ('chatbot_kichbanchatbot', 'chatbot_buocchatbot', 'chatbot_sodokichban')


def restore_scripts_from_sqlite(new_path, old_path):
    """
    Chép dữ liệu kịch bản (kịch bản, các bước, sơ đồ kéo thả) từ DB cũ sang DB hiện tại.
    Chỉ chép các cột có ở cả hai bên, bỏ qua dòng đã tồn tại. Không đụng tới bảng khác.
    Trả về {tên bảng: số dòng đã chép, hoặc None nếu bảng không có ở một trong hai DB}.
    """
    import sqlite3

    result = {}
    con = sqlite3.connect(str(new_path))
    try:
        con.execute("ATTACH DATABASE ? AS old", (str(old_path),))
        for table in RESTORE_TABLES:
            old_cols = [r[1] for r in con.execute(f'PRAGMA old.table_info("{table}")')]
            new_cols = [r[1] for r in con.execute(f'PRAGMA main.table_info("{table}")')]
            if not old_cols or not new_cols:
                result[table] = None
                continue
            cols = ', '.join(f'"{c}"' for c in new_cols if c in old_cols)
            before = con.execute(f'SELECT COUNT(*) FROM main."{table}"').fetchone()[0]
            con.execute(f'INSERT OR IGNORE INTO main."{table}" ({cols}) SELECT {cols} FROM old."{table}"')
            result[table] = con.execute(f'SELECT COUNT(*) FROM main."{table}"').fetchone()[0] - before
        con.commit()
    finally:
        con.close()
    return result
