"""
Các view quản lý kịch bản chatbot dạng kéo thả (Flow Builder).
Thay thế 4 view cũ trong views.py: admin_script_create / detail / edit / preview.
Các view list, delete, toggle_status vẫn dùng bản trong views.py.
"""
import json
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from . import flow_utils, identity
from .models import KichBanChatbot


def admin_script_create(request):
    """Tạo kịch bản mới với sơ đồ khởi tạo: Bắt đầu -> Chào mừng."""
    if request.method != 'POST':
        return redirect('chatbot:admin_script_list')

    ten_kb = (request.POST.get('ten_kich_ban') or '').strip()
    if not ten_kb:
        messages.error(request, 'Vui lòng nhập tên kịch bản.')
        return redirect('chatbot:admin_script_list')
    if KichBanChatbot.objects.filter(ten_kich_ban=ten_kb).exists():
        messages.error(request, 'Tên kịch bản đã tồn tại, vui lòng chọn tên khác.')
        return redirect('chatbot:admin_script_list')

    with transaction.atomic():
        script = KichBanChatbot.objects.create(
            ma_kb=f"KB{uuid.uuid4().hex[:6].upper()}",
            ten_kich_ban=ten_kb[:150],
            mo_ta=(request.POST.get('mo_ta') or '').strip(),
            trang_thai='Đang hoạt động',
        )
        flow_utils.save_graph(script, flow_utils.sanitize_graph(flow_utils.build_starter_graph()))
    messages.success(request, 'Tạo kịch bản thành công!')
    return redirect('chatbot:admin_script_edit', pk=script.pk)


def admin_script_detail(request, pk):
    """Chi tiết kịch bản: sơ đồ chỉ xem."""
    script = get_object_or_404(KichBanChatbot, pk=pk)
    return render(request, 'chatbot/admin_script_detail.html', {
        'script': script,
        'graph': flow_utils.load_graph(script),
    })


def admin_script_edit(request, pk):
    """Chỉnh sửa kịch bản: trình dựng kéo thả. Việc lưu dữ liệu đi qua admin_script_graph_save."""
    script = get_object_or_404(KichBanChatbot, pk=pk)
    return render(request, 'chatbot/admin_script_edit.html', {
        'script': script,
        'graph': flow_utils.load_graph(script),
    })


def admin_script_preview(request, pk):
    """Xem trước: mô phỏng chatbot chạy theo sơ đồ đã lưu."""
    script = get_object_or_404(KichBanChatbot, pk=pk)
    return render(request, 'chatbot/admin_script_preview.html', {
        'script': script,
        'graph': flow_utils.load_graph(script),
    })


@require_POST
def admin_script_graph_save(request, pk):
    """API lưu sơ đồ (JSON). Trình duyệt gọi bằng fetch kèm CSRF token."""
    if not request.user.is_authenticated:
        return JsonResponse(
            {'ok': False, 'error': 'Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.'}, status=401)
    if not identity.is_staff_user(request.user):
        return JsonResponse({'ok': False, 'error': 'Bạn không có quyền thực hiện thao tác này.'}, status=403)

    script = get_object_or_404(KichBanChatbot, pk=pk)
    try:
        payload = json.loads(request.body.decode('utf-8'))
        if not isinstance(payload, dict):
            raise ValueError('Dữ liệu gửi lên không hợp lệ.')
        graph = flow_utils.sanitize_graph(payload.get('graph'))
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Dữ liệu gửi lên không đọc được.'}, status=400)
    except (ValueError, UnicodeDecodeError) as exc:
        return JsonResponse({'ok': False, 'error': str(exc) or 'Dữ liệu không hợp lệ.'}, status=400)

    with transaction.atomic():
        graph = flow_utils.save_graph(script, graph)
    return JsonResponse({'ok': True, 'graph': graph, 'saved_at': timezone.localtime().strftime('%H:%M:%S')})


@require_GET
def script_graph_api(request):
    """API công khai: trả sơ đồ của kịch bản đang hoạt động để widget chatbot chạy theo (dùng ở bước sau)."""
    script = KichBanChatbot.objects.filter(trang_thai='Đang hoạt động').order_by('pk').first()
    if script is None:
        return JsonResponse({'ok': False, 'graph': None})
    graph = flow_utils.load_graph(script)
    for node in graph['nodes']:
        node.pop('ma_buoc', None)
    return JsonResponse({'ok': True, 'script': script.ten_kich_ban, 'graph': graph})


# --------------------------------------------------------------------------
# Tải ảnh lên cho hộp "Hình ảnh"
# Ảnh lưu tại <BASE_DIR>/media/chatbot/ và được phục vụ qua /chatbot/media/<tên>,
# nên không cần cấu hình MEDIA_ROOT / MEDIA_URL trong settings.
# --------------------------------------------------------------------------
def _upload_dir():
    folder = Path(settings.BASE_DIR) / 'media' / 'chatbot'
    folder.mkdir(parents=True, exist_ok=True)
    return folder


@require_POST
def admin_script_image_upload(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {'ok': False, 'error': 'Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.'}, status=401)
    if not identity.is_staff_user(request.user):
        return JsonResponse({'ok': False, 'error': 'Bạn không có quyền thực hiện thao tác này.'}, status=403)

    upload = request.FILES.get('image')
    if upload is None:
        return JsonResponse({'ok': False, 'error': 'Chưa chọn ảnh.'}, status=400)
    if upload.size > flow_utils.IMAGE_MAX_BYTES:
        return JsonResponse({'ok': False, 'error': 'Ảnh quá lớn, tối đa 5 MB.'}, status=400)

    ext = flow_utils.detect_image_ext(upload.read(16))
    upload.seek(0)
    if ext is None:
        return JsonResponse(
            {'ok': False, 'error': 'Chỉ nhận ảnh JPG, PNG, WEBP hoặc GIF.'}, status=400)

    name = f"{uuid.uuid4().hex}.{ext}"
    with open(_upload_dir() / name, 'wb') as out:
        for chunk in upload.chunks():
            out.write(chunk)
    return JsonResponse({'ok': True, 'url': reverse('chatbot:script_media', args=[name])})


@require_GET
def script_media(request, name):
    """Phục vụ ảnh đã tải lên (công khai, vì ảnh hiển thị trong chatbot cho khách)."""
    if not flow_utils.MEDIA_NAME_RE.match(name):
        raise Http404
    path = _upload_dir() / name
    if not path.is_file():
        raise Http404
    response = FileResponse(open(path, 'rb'),
                            content_type=flow_utils.IMAGE_CONTENT_TYPES[name.rsplit('.', 1)[1]])
    response['Cache-Control'] = 'public, max-age=86400'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
