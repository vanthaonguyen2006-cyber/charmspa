"""
Chatbot khách hàng chạy theo kịch bản + trang quản lý hội thoại (Admin / CSKH).

Phần A - API cho widget trên website khách hàng:
    chat_me, chat_flow, chat_consult, chat_state, chat_send
Phần B - Trang quản lý hội thoại theo báo cáo:
    admin_conversation_list / detail / accept / reply / complete / messages
"""
import csv
import json
import re
import uuid
from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages as dj_messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from accounts.models import NhanVien

from . import chat_logic as cl
from . import flow_utils
from .models import BuocChatbot, PhienHoiThoai, TinNhan, YeuCauTuVan
from .views import get_or_create_session

SESSION_RE = re.compile(r'^[A-Za-z0-9]{6,10}$')
MAX_MESSAGE_LEN = 1000
PAGE_SIZE = 10


# ==========================================================================
# Tiện ích dùng chung
# ==========================================================================
def _json(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _err(message, status=400):
    return JsonResponse({'ok': False, 'error': message}, status=status)


def _sid(value):
    value = str(value or '').strip()[:10]
    return value if SESSION_RE.match(value) else ''


def _first(obj, *names):
    """Giá trị chuỗi không rỗng đầu tiên trong các thuộc tính của obj (an toàn khi thiếu thuộc tính)."""
    if obj is None:
        return ''
    for name in names:
        value = getattr(obj, name, None)
        if value:
            return str(value).strip()
    return ''


def _local(dt):
    """Đổi sang giờ địa phương nếu dữ liệu có múi giờ (chạy được cả khi USE_TZ = False)."""
    if dt is not None and timezone.is_aware(dt):
        return timezone.localtime(dt)
    return dt


def _now_local():
    return _local(timezone.now())


def _fmt(dt, pattern):
    return _local(dt).strftime(pattern) if dt else ''


def customer_contact(user):
    """Thông tin khách đã đăng nhập: {fullname, phone, email}; None nếu là khách vãng lai."""
    if not getattr(user, 'is_authenticated', False):
        return None
    kh = getattr(user, 'khachhang', None)
    if kh is None:
        return None
    full_name = getattr(user, 'get_full_name', lambda: '')() or ''
    return {
        'fullname': _first(kh, 'ho_ten', 'ho_va_ten', 'ten_khach_hang', 'ten')
                    or full_name.strip() or user.get_username(),
        'phone': _first(kh, 'so_dien_thoai', 'sdt', 'phone'),
        'email': _first(kh, 'email') or (getattr(user, 'email', '') or '').strip(),
    }


def staff_identity(user):
    """(NhanVien hoặc None, tên hiển thị) của nhân viên đang đăng nhập."""
    nv = getattr(user, 'nhanvien', None)
    if not isinstance(nv, NhanVien):
        nv = None
    full_name = getattr(user, 'get_full_name', lambda: '')() or ''
    name = _first(nv, 'ho_ten', 'ho_va_ten', 'ten_nhan_vien', 'ten') or full_name.strip() or user.get_username()
    return nv, name


def _latest_request(phien):
    return YeuCauTuVan.objects.filter(ma_pht=phien).order_by('-thoi_gian_yeu_cau').first()


def _log(phien, sender, text, node=None, nv=None):
    buoc = None
    ma_buoc = (node or {}).get('ma_buoc')
    if ma_buoc and BuocChatbot.objects.filter(pk=ma_buoc).exists():
        buoc = BuocChatbot.objects.get(pk=ma_buoc)
    return TinNhan.objects.create(
        ma_tn=f"TN{uuid.uuid4().hex[:8].upper()}",
        ma_pht=phien,
        ma_nv=nv,
        ma_buoc=buoc,
        loai_nguoi_gui=sender,
        noi_dung=text,
    )


def _can_access(request, phien):
    """Hội thoại gắn với một khách hàng thì chỉ chính khách đó được xem."""
    if phien.ma_kh_id is None:
        return True
    kh = getattr(request.user, 'khachhang', None) if request.user.is_authenticated else None
    return kh is not None and kh.pk == phien.ma_kh_id


def _graph_of(phien):
    if phien.ma_kb_id:
        return flow_utils.load_graph(phien.ma_kb)
    return flow_utils.sanitize_graph(flow_utils.build_default_graph())


def _msg_payload(tn):
    return {
        'id': tn.ma_tn,
        'sender': tn.loai_nguoi_gui,
        'content': cl.plain_text(tn.noi_dung),
        'time': _fmt(tn.thoi_gian, '%H:%M'),
    }


def _request_summary(yc):
    info = cl.parse_request_text(yc.noi_dung)
    return {
        'fullname': info['fullname'] or 'Khách hàng',
        'phone': info['phone'],
        'email': info['email'],
        'topic': info['topic'] or 'Tư vấn chung',
    }


# ==========================================================================
# PHẦN A - API cho widget khách hàng
# ==========================================================================
@ensure_csrf_cookie
@require_GET
def chat_me(request):
    """Cho widget biết khách đã đăng nhập chưa và thông tin tài khoản để tự điền. Đồng thời đặt cookie CSRF."""
    info = customer_contact(request.user)
    if info is None:
        return JsonResponse({'authenticated': False})
    return JsonResponse({'authenticated': True, **info})


@require_POST
def chat_flow(request):
    """Đi theo sơ đồ kịch bản. Máy chủ xác định bước tiếp theo nên khách không thể nhảy tới bước tùy ý."""
    data = _json(request)
    sid = _sid(data.get('session_id')) if data else ''
    if not sid:
        return _err('Phiên trò chuyện không hợp lệ.')

    phien = get_or_create_session(sid, request.user)
    if not _can_access(request, phien):
        return _err('Không có quyền truy cập hội thoại này.', 403)
    graph = _graph_of(phien)

    node_id = str(data.get('node_id') or '')[:40]
    if not node_id:                                   # bắt đầu kịch bản
        target = cl.start_target(graph)
        if target is not None and not TinNhan.objects.filter(ma_pht=phien).exists():
            _log(phien, 'Chatbot', cl.node_log_text(target), target)
    else:
        source = cl.node_by_id(graph, node_id)
        option = cl.option_by_id(source, str(data.get('option_id') or '')[:40]) if source else None
        if option is None:
            return _err('Lựa chọn không hợp lệ.')
        _log(phien, 'Khách hàng', option['text'] or 'Lựa chọn')
        target = cl.node_by_id(graph, option['nextId']) if option['nextId'] else None
        if target is not None:
            _log(phien, 'Chatbot', cl.node_log_text(target), target)

    return JsonResponse({'ok': True, 'node': cl.public_node(target) if target else None})


@require_POST
def chat_consult(request):
    """Khách gửi yêu cầu tư vấn trực tiếp. Khách đã đăng nhập: thông tin lấy từ tài khoản (bỏ qua dữ liệu gửi lên)."""
    data = _json(request)
    sid = _sid(data.get('session_id')) if data else ''
    if not sid:
        return _err('Phiên trò chuyện không hợp lệ.')

    phien = get_or_create_session(sid, request.user)
    if not _can_access(request, phien):
        return _err('Không có quyền truy cập hội thoại này.', 403)

    cleaned, error = cl.clean_consult(data, customer_contact(request.user))
    if error:
        return _err(error)

    yc = _latest_request(phien)
    if yc is None or yc.trang_thai == cl.STATUS_DONE:
        yc = YeuCauTuVan.objects.create(
            ma_yctv=f"YC{uuid.uuid4().hex[:8].upper()}",
            ma_pht=phien,
            noi_dung=cl.build_request_text(cleaned),
            trang_thai=cl.STATUS_WAITING,
        )
        phien.trang_thai = cl.STATUS_WAITING
        phien.ket_qua_xu_ly = 'Chuyển tư vấn viên'
        phien.save()
        _log(phien, 'Khách hàng', f"Yêu cầu tư vấn: {cleaned['topic']}")
        _log(phien, 'Chatbot', 'Yêu cầu của bạn đã được gửi. Vui lòng chờ nhân viên tiếp nhận.')

    return JsonResponse({'ok': True, 'status': yc.trang_thai, 'request': _request_summary(yc)})


@require_GET
def chat_state(request):
    """Trạng thái hội thoại + tin nhắn, widget gọi định kỳ khi đang tư vấn trực tiếp."""
    sid = _sid(request.GET.get('session_id'))
    phien = PhienHoiThoai.objects.filter(pk=sid).first() if sid else None
    if phien is None or not _can_access(request, phien):
        return JsonResponse({'ok': True, 'exists': False})

    yc = _latest_request(phien)
    msgs = list(TinNhan.objects.filter(ma_pht=phien).order_by('-thoi_gian')[:200])
    msgs.reverse()
    payload = {
        'ok': True,
        'exists': True,
        'has_request': yc is not None,
        'status': yc.trang_thai if yc else '',
        'staff_name': '',
        'request': None,
        'messages': [_msg_payload(m) for m in msgs],
    }
    if yc is not None:
        payload['request'] = _request_summary(yc)
        if yc.trang_thai != cl.STATUS_WAITING:
            payload['staff_name'] = yc.nguoi_tiep_nhan or 'Nhân viên tư vấn'
    return JsonResponse(payload)


@require_POST
def chat_send(request):
    """Khách nhắn tin cho nhân viên (chỉ sau khi nhân viên đã tiếp nhận)."""
    data = _json(request)
    sid = _sid(data.get('session_id')) if data else ''
    text = str((data or {}).get('message') or '').strip()
    if not sid or not text:
        return _err('Tin nhắn trống.')
    if len(text) > MAX_MESSAGE_LEN:
        return _err(f'Tin nhắn quá dài (tối đa {MAX_MESSAGE_LEN} ký tự).')

    phien = PhienHoiThoai.objects.filter(pk=sid).first()
    if phien is None or not _can_access(request, phien):
        return _err('Phiên trò chuyện không tồn tại.', 404)
    yc = _latest_request(phien)
    if yc is None:
        return _err('Bạn chưa gửi yêu cầu tư vấn trực tiếp.', 409)
    if yc.trang_thai == cl.STATUS_WAITING:
        return _err('Vui lòng đợi nhân viên tiếp nhận yêu cầu.', 409)
    if yc.trang_thai == cl.STATUS_DONE:
        return _err('Cuộc tư vấn đã kết thúc.', 409)

    tn = _log(phien, 'Khách hàng', text)
    return JsonResponse({'ok': True, 'id': tn.ma_tn, 'time': _fmt(tn.thoi_gian, '%H:%M')})


# ==========================================================================
# PHẦN B - Quản lý hội thoại (Admin / CSKH)
# ==========================================================================
def _short(text, limit=70):
    text = ' '.join(cl.plain_text(text).split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + '…'


def _conversation_rows():
    """Danh sách hội thoại kèm khách hàng, nội dung gần nhất, nhân viên, trạng thái. Mới nhất trước."""
    sessions = list(PhienHoiThoai.objects.select_related('ma_kh').order_by('-thoi_gian_bat_dau')[:1000])
    ids = [s.pk for s in sessions]

    requests_by_session = {}
    for yc in YeuCauTuVan.objects.filter(ma_pht_id__in=ids).order_by('thoi_gian_yeu_cau'):
        requests_by_session[yc.ma_pht_id] = yc          # bản ghi sau (mới hơn) ghi đè bản trước

    last_by_session = {}
    for row in (TinNhan.objects.filter(ma_pht_id__in=ids).order_by('thoi_gian')
                .values('ma_pht_id', 'noi_dung', 'thoi_gian')):
        last_by_session[row['ma_pht_id']] = row

    rows = []
    for s in sessions:
        yc = requests_by_session.get(s.pk)
        last = last_by_session.get(s.pk)
        info = _request_summary(yc) if yc else {'fullname': '', 'phone': '', 'email': '', 'topic': ''}
        kh = s.ma_kh
        name = info['fullname'] or _first(kh, 'ho_ten', 'ho_va_ten', 'ten_khach_hang', 'ten') or 'Khách vãng lai'
        phone = info['phone'] or _first(kh, 'so_dien_thoai', 'sdt', 'phone')
        last_time = last['thoi_gian'] if last else s.thoi_gian_bat_dau
        rows.append({
            'id': s.pk,
            'name': name,
            'phone': phone if phone and phone != 'Chưa cung cấp' else '',
            'email': info['email'] if info['email'] != 'Chưa cung cấp' else '',
            'topic': info['topic'],
            'last_text': _short(last['noi_dung']) if last else 'Chưa có tin nhắn',
            'last_time': last_time,
            'time_label': _fmt(last_time, '%H:%M %d/%m'),
            'staff': (yc.nguoi_tiep_nhan or ('Nhân viên tư vấn' if yc.trang_thai != cl.STATUS_WAITING else ''))
                     if yc else '',
            'status': cl.derive_status(yc is not None, yc.trang_thai if yc else ''),
        })
    rows.sort(key=lambda r: _local(r['last_time']) if r['last_time'] else _now_local(), reverse=True)
    return rows


def _filter_rows(rows, q, period):
    if period in ('today', '7', '30'):
        days = {'today': 0, '7': 7, '30': 30}[period]
        since = _now_local().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)
        rows = [r for r in rows if r['last_time'] and _local(r['last_time']) >= since]
    if q:
        needle = q.lower()
        rows = [r for r in rows if needle in ' '.join(
            [r['name'], r['phone'], r['email'], r['last_text'], r['id'], r['topic']]).lower()]
    return rows


def admin_conversation_list(request):
    """Quản lý hội thoại: tab trạng thái có số lượng, tìm kiếm, lọc thời gian, phân trang, xuất báo cáo."""
    q = (request.GET.get('q') or '').strip()[:100]
    status = request.GET.get('status') or ''
    period = request.GET.get('period') or 'all'
    if status not in (cl.STATUS_WAITING, cl.STATUS_ACTIVE, cl.STATUS_DONE, cl.STATUS_BOT):
        status = ''
    if period not in ('today', '7', '30', 'all'):
        period = 'all'

    base = _filter_rows(_conversation_rows(), q, period)
    counts = {
        '': len(base),
        cl.STATUS_WAITING: sum(1 for r in base if r['status'] == cl.STATUS_WAITING),
        cl.STATUS_ACTIVE: sum(1 for r in base if r['status'] == cl.STATUS_ACTIVE),
        cl.STATUS_DONE: sum(1 for r in base if r['status'] == cl.STATUS_DONE),
    }
    rows = [r for r in base if r['status'] == status] if status else base

    if request.GET.get('export') == 'csv':
        return _export_csv(rows)

    def link(**changes):
        params = {'q': q, 'status': status, 'period': period}
        params.update(changes)
        return '?' + urlencode({k: v for k, v in params.items() if v and not (k == 'period' and v == 'all')})

    total = len(rows)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    try:
        page = min(max(int(request.GET.get('page', 1)), 1), pages)
    except ValueError:
        page = 1
    start = (page - 1) * PAGE_SIZE
    tabs = [{'label': label, 'count': counts[key], 'active': status == key, 'url': link(status=key, page='')}
            for label, key in (('Tất cả', ''), ('Chờ xử lý', cl.STATUS_WAITING),
                               ('Đang xử lý', cl.STATUS_ACTIVE), ('Đã hoàn tất', cl.STATUS_DONE))]

    return render(request, 'chatbot/admin_conversation_list.html', {
        'rows': rows[start:start + PAGE_SIZE],
        'tabs': tabs,
        'q': q, 'status': status, 'period': period,
        'total': total,
        'first': start + 1 if total else 0,
        'last': min(start + PAGE_SIZE, total),
        'page': page,
        'page_links': [{'n': n, 'url': link(page=n), 'active': n == page} for n in range(1, pages + 1)],
        'prev_url': link(page=page - 1) if page > 1 else '',
        'next_url': link(page=page + 1) if page < pages else '',
        'export_url': link(export='csv', page=''),
    })


def _export_csv(rows):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="hoi_thoai_{_now_local():%Y%m%d_%H%M}.csv"'
    response.write('\ufeff')                       # BOM để Excel đọc đúng tiếng Việt
    writer = csv.writer(response)
    writer.writerow(['Mã hội thoại', 'Khách hàng', 'Số điện thoại', 'Email', 'Nhu cầu',
                     'Nội dung gần nhất', 'Thời gian', 'Nhân viên phụ trách', 'Trạng thái'])
    for r in rows:
        writer.writerow([r['id'], r['name'], r['phone'], r['email'], r['topic'],
                         r['last_text'], r['time_label'], r['staff'] or 'Chưa có người xử lý', r['status']])
    return response


def admin_conversation_detail(request, session_id):
    """Chi tiết hội thoại: danh sách trong ngày | nội dung trao đổi | thông tin khách và lịch sử xử lý."""
    conv = get_object_or_404(PhienHoiThoai, ma_pht=session_id)
    yc = _latest_request(conv)
    info = _request_summary(yc) if yc else {'fullname': '', 'phone': '', 'email': '', 'topic': ''}
    kh = conv.ma_kh
    customer = {
        'fullname': info['fullname'] or _first(kh, 'ho_ten', 'ho_va_ten', 'ten_khach_hang', 'ten') or 'Khách vãng lai',
        'phone': info['phone'] or _first(kh, 'so_dien_thoai', 'sdt', 'phone') or 'Chưa cung cấp',
        'email': info['email'] or 'Chưa cung cấp',
        'topic': info['topic'] or 'Tư vấn chung',
    }

    staff_name = ''
    events = []
    if yc is not None:
        events.append({'text': 'Khách hàng gửi yêu cầu tư vấn trực tiếp', 'dt': yc.thoi_gian_yeu_cau})
        if yc.thoi_gian_tiep_nhan or yc.trang_thai != cl.STATUS_WAITING:
            staff_name = yc.nguoi_tiep_nhan or 'Nhân viên tư vấn'
            events.append({'text': f'{staff_name} đã tiếp nhận hội thoại', 'dt': yc.thoi_gian_tiep_nhan})
        if yc.trang_thai == cl.STATUS_DONE:
            events.append({'text': f'{staff_name or "Nhân viên"} đã hoàn tất hội thoại',
                           'dt': yc.thoi_gian_hoan_tat})

    msgs = list(TinNhan.objects.filter(ma_pht=conv).order_by('thoi_gian'))
    timeline = cl.build_timeline(
        [{'id': m.ma_tn, 'sender': m.loai_nguoi_gui, 'content': cl.plain_text(m.noi_dung), 'dt': m.thoi_gian}
         for m in msgs],
        events)
    for item in timeline:
        item['time'] = _fmt(item['dt'], '%H:%M')
        item['date'] = _fmt(item['dt'], '%d/%m/%Y')
    history = [{'text': e['text'], 'time': _fmt(e['dt'], '%H:%M %d/%m/%Y')} for e in events if e.get('dt')]

    status = cl.derive_status(yc is not None, yc.trang_thai if yc else '')
    sidebar = _conversation_rows()[:15]
    return render(request, 'chatbot/admin_conversation_detail.html', {
        'conversation': conv,
        'customer': customer,
        'timeline': timeline,
        'history': history,
        'status': status,
        'has_request': yc is not None,
        'accepted': yc is not None and yc.trang_thai != cl.STATUS_WAITING,
        'completed': status == cl.STATUS_DONE,
        'staff_name': staff_name,
        'note': yc.ghi_chu_xu_ly if yc else '',
        'message_count': len(msgs),
        'sidebar': sidebar,
    })


def _accept(yc, user):
    """Tiếp nhận có điều kiện (tránh hai nhân viên cùng nhận). Trả về (ok, tên nhân viên)."""
    nv, name = staff_identity(user)
    updated = YeuCauTuVan.objects.filter(pk=yc.pk, trang_thai=cl.STATUS_WAITING).update(
        trang_thai=cl.STATUS_ACTIVE,
        thoi_gian_tiep_nhan=timezone.now(),
        nguoi_tiep_nhan=name,
        ma_nv=nv,
    )
    if updated:
        PhienHoiThoai.objects.filter(pk=yc.ma_pht_id).update(trang_thai=cl.STATUS_ACTIVE)
        return True, name
    yc.refresh_from_db()
    owner = yc.nguoi_tiep_nhan
    return (yc.trang_thai == cl.STATUS_ACTIVE and (not owner or owner == name)), name


def _need_login():
    return _err('Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.', 401)


@require_POST
def admin_conversation_accept(request, session_id):
    if not request.user.is_authenticated:
        return _need_login()
    conv = get_object_or_404(PhienHoiThoai, ma_pht=session_id)
    yc = _latest_request(conv)
    if yc is None:
        return _err('Khách hàng chưa gửi yêu cầu tư vấn trực tiếp.', 409)
    if yc.trang_thai == cl.STATUS_DONE:
        return _err('Hội thoại đã hoàn tất.', 409)
    ok, name = _accept(yc, request.user)
    if not ok:
        return _err('Hội thoại đã được nhân viên khác tiếp nhận.', 409)
    return JsonResponse({'ok': True, 'staff': name})


@require_POST
def admin_conversation_reply(request, session_id):
    """Nhân viên nhắn cho khách. Nếu hội thoại còn chờ thì tự động tiếp nhận."""
    if not request.user.is_authenticated:
        return _need_login()
    data = _json(request)
    text = str((data or {}).get('message') or '').strip()
    if not text:
        return _err('Vui lòng nhập nội dung phản hồi.')
    if len(text) > MAX_MESSAGE_LEN:
        return _err(f'Tin nhắn quá dài (tối đa {MAX_MESSAGE_LEN} ký tự).')

    conv = get_object_or_404(PhienHoiThoai, ma_pht=session_id)
    yc = _latest_request(conv)
    if yc is None:
        return _err('Khách hàng chưa gửi yêu cầu tư vấn trực tiếp.', 409)
    if yc.trang_thai == cl.STATUS_DONE:
        return _err('Hội thoại đã hoàn tất, không thể gửi thêm tin nhắn.', 409)

    nv, name = staff_identity(request.user)
    if yc.trang_thai == cl.STATUS_WAITING:
        ok, _name = _accept(yc, request.user)
        if not ok:
            return _err('Hội thoại đã được nhân viên khác tiếp nhận.', 409)
    elif yc.nguoi_tiep_nhan and yc.nguoi_tiep_nhan != name:
        return _err(f'Hội thoại đang được {yc.nguoi_tiep_nhan} xử lý.', 409)

    tn = _log(conv, 'Nhân viên', text, nv=nv)
    return JsonResponse({'ok': True, 'id': tn.ma_tn, 'time': _fmt(tn.thoi_gian, '%H:%M'), 'staff': name})


def admin_conversation_complete(request, session_id):
    """Xác nhận hoàn tất hội thoại từ hộp thoại (kèm ghi chú xử lý)."""
    if request.method != 'POST':
        return redirect('chatbot:admin_conversation_detail', session_id=session_id)
    if not request.user.is_authenticated:
        dj_messages.error(request, 'Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.')
        return redirect('chatbot:admin_conversation_detail', session_id=session_id)

    conv = get_object_or_404(PhienHoiThoai, ma_pht=session_id)
    note = (request.POST.get('ghi_chu_xu_ly') or '').strip()[:1000]
    nv, name = staff_identity(request.user)
    now = timezone.now()

    open_requests = YeuCauTuVan.objects.filter(ma_pht=conv).exclude(trang_thai=cl.STATUS_DONE)
    for yc in open_requests:
        yc.trang_thai = cl.STATUS_DONE
        yc.thoi_gian_hoan_tat = now
        yc.ghi_chu_xu_ly = note
        if not yc.nguoi_tiep_nhan:
            yc.nguoi_tiep_nhan = name
        if not yc.thoi_gian_tiep_nhan:
            yc.thoi_gian_tiep_nhan = now
        if yc.ma_nv_id is None and nv is not None:
            yc.ma_nv = nv
        yc.save()

    conv.trang_thai = cl.STATUS_DONE
    conv.thoi_gian_ket_thuc = now
    conv.ket_qua_xu_ly = 'Chuyển tư vấn viên' if YeuCauTuVan.objects.filter(ma_pht=conv).exists() else 'Đã giải đáp'
    conv.save()
    dj_messages.success(request, 'Hội thoại đã được đánh dấu Hoàn tất.')
    return redirect('chatbot:admin_conversation_detail', session_id=session_id)


@require_GET
def admin_conversation_messages(request, session_id):
    """Cho trang chi tiết cập nhật tin nhắn mới của khách (polling)."""
    conv = get_object_or_404(PhienHoiThoai, ma_pht=session_id)
    yc = _latest_request(conv)
    msgs = TinNhan.objects.filter(ma_pht=conv).order_by('thoi_gian')
    return JsonResponse({
        'ok': True,
        'status': cl.derive_status(yc is not None, yc.trang_thai if yc else ''),
        'messages': [_msg_payload(m) for m in msgs],
    })
