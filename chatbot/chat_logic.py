"""
Logic thuần Python (không phụ thuộc Django) cho chatbot khách hàng và trang quản lý hội thoại.
Tách riêng để dễ kiểm thử.
"""
import re

PHONE_RE = re.compile(r'^\+?\d[\d\s.\-]{7,14}\d$')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
TAG_RE = re.compile(r'<[^>]+>')
BR_RE = re.compile(r'<\s*br\s*/?\s*>', re.I)

DEFAULT_NEEDS = ['Chọn liệu trình', 'Hỗ trợ đặt lịch', 'Chăm sóc sau liệu trình', 'Khác']
HANDOFF_TYPES = ('form', 'chuyen_nhan_vien', 'chat_truc_tiep')

STATUS_WAITING = 'Chờ xử lý'
STATUS_ACTIVE = 'Đang xử lý'
STATUS_DONE = 'Đã hoàn tất'
STATUS_BOT = 'Chatbot'


def plain_text(text):
    """Bỏ thẻ HTML trong tin nhắn cũ (chatbot cũ lưu HTML) để hiển thị an toàn."""
    text = BR_RE.sub('\n', text or '')
    text = TAG_RE.sub('', text)
    return text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').strip()


# ----------------------------- Luồng kịch bản -----------------------------
def node_by_id(graph, node_id):
    for node in graph.get('nodes', []):
        if node['id'] == node_id:
            return node
    return None


def start_target(graph):
    """Bước đầu tiên mà khối 'Bắt đầu' trỏ tới (hoặc None)."""
    for node in graph.get('nodes', []):
        if node['type'] == 'bat_dau':
            for opt in node['options']:
                if opt['nextId']:
                    return node_by_id(graph, opt['nextId'])
    return None


def option_by_id(node, option_id):
    for opt in node.get('options', []):
        if opt['id'] == option_id:
            return opt
    return None


def public_node(node):
    """Dữ liệu một bước gửi cho trình duyệt khách (không lộ tọa độ, mã bước nội bộ)."""
    return {
        'id': node['id'],
        'type': node['type'],
        'title': node.get('title', ''),
        'content': node.get('content', ''),
        'image_url': node.get('image_url', '') if node['type'] == 'hinh_anh' else '',
        'duration': node.get('duration', 0),
        'price': node.get('price', 0),
        'handoff': node['type'] in HANDOFF_TYPES,
        'options': [{'id': o['id'], 'text': o['text']} for o in node.get('options', [])],
    }


def node_log_text(node):
    """Nội dung ghi vào lịch sử hội thoại cho tin nhắn chatbot của một bước."""
    t = node['type']
    if t == 'dich_vu':
        price = f"{int(node.get('price') or 0):,}".replace(',', '.')
        parts = [node.get('title', ''), f"{node.get('duration') or 0} phút · {price}đ", node.get('content', '')]
        return '\n'.join(p for p in parts if p)
    if t == 'hinh_anh':
        return ('[Hình ảnh] ' + (node.get('content') or node.get('title') or '')).strip()
    if t in HANDOFF_TYPES:
        return 'Quý khách vui lòng để lại thông tin để nhân viên tư vấn hỗ trợ trực tiếp.'
    return node.get('content') or node.get('title') or ''


# ----------------------------- Yêu cầu tư vấn -----------------------------
def _clean_value(value, limit):
    return str(value or '').replace('|', '/').replace('\r', ' ').replace('\n', ' ').strip()[:limit]


def clean_consult(data, account):
    """
    Kiểm tra dữ liệu yêu cầu tư vấn.
    - account: dict {fullname, phone, email} nếu khách đã đăng nhập (ưu tiên, bỏ qua dữ liệu khách gửi lên);
      None nếu là khách vãng lai.
    Trả về (cleaned, error). error là None nếu hợp lệ.
    """
    topic = _clean_value(data.get('topic'), 100) or 'Tư vấn chung'
    if account:
        return {
            'fullname': _clean_value(account.get('fullname'), 100) or 'Khách hàng',
            'phone': _clean_value(account.get('phone'), 20),
            'email': _clean_value(account.get('email'), 100),
            'topic': topic,
        }, None

    fullname = _clean_value(data.get('fullname'), 100)
    phone = _clean_value(data.get('phone'), 20)
    email = _clean_value(data.get('email'), 100)
    if len(fullname) < 2:
        return None, 'Vui lòng nhập họ và tên.'
    if not phone and not email:
        return None, 'Vui lòng nhập số điện thoại hoặc email để nhân viên liên hệ.'
    if phone and not PHONE_RE.match(phone):
        return None, 'Số điện thoại chưa hợp lệ.'
    if email and not EMAIL_RE.match(email):
        return None, 'Email chưa hợp lệ.'
    return {'fullname': fullname, 'phone': phone, 'email': email, 'topic': topic}, None


def build_request_text(c):
    return (f"Họ tên: {c['fullname']} | SĐT: {c['phone'] or 'Chưa cung cấp'} | "
            f"Email: {c['email'] or 'Chưa cung cấp'} | Nhu cầu: {c['topic']}")


def parse_request_text(raw):
    info = {'fullname': '', 'phone': '', 'email': '', 'topic': ''}
    raw = raw or ''
    if '|' in raw:
        for part in raw.split('|'):
            for key, label in (('fullname', 'Họ tên:'), ('phone', 'SĐT:'), ('email', 'Email:'), ('topic', 'Nhu cầu:')):
                if label in part:
                    info[key] = part.replace(label, '').strip()
    else:
        info['topic'] = raw.replace('Khách yêu cầu tư vấn:', '').strip()
    return info


# ----------------------------- Trạng thái & dòng thời gian -----------------------------
def derive_status(has_request, request_status):
    """Hội thoại chưa có yêu cầu tư vấn chỉ có chatbot -> 'Chatbot'."""
    if not has_request:
        return STATUS_BOT
    return request_status if request_status in (STATUS_WAITING, STATUS_ACTIVE, STATUS_DONE) else STATUS_WAITING


def build_timeline(messages, events):
    """
    Gộp tin nhắn và sự kiện hệ thống thành một dòng thời gian theo thời gian.
    messages: [{'id','sender','content','dt'}], events: [{'text','dt'}]
    """
    items = []
    for m in messages:
        items.append({'kind': 'msg', 'id': m['id'], 'sender': m['sender'], 'content': m['content'], 'dt': m['dt']})
    for e in events:
        if e.get('dt') is not None:
            items.append({'kind': 'sys', 'id': '', 'sender': '', 'content': e['text'], 'dt': e['dt']})
    items.sort(key=lambda x: (x['dt'], 0 if x['kind'] == 'sys' else 1))
    return items
