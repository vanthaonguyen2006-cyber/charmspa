import json
import uuid
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import PhienHoiThoai, TinNhan, BuocChatbot, KichBanChatbot, YeuCauTuVan

# Thử kết nối Model Dịch vụ từ app dịch vụ (nếu có)
try:
    from services.models import DichVu
except ImportError:
    DichVu = None


def get_or_create_session(session_id, user):
    """Khởi tạo hoặc lấy phiên hội thoại an toàn theo User"""
    session_key = str(session_id)[:10]

    kich_ban_default = KichBanChatbot.objects.filter(trang_thai='Đang hoạt động').first()
    if not kich_ban_default:
        kich_ban_default, _ = KichBanChatbot.objects.get_or_create(
            ma_kb="KB001",
            defaults={
                'ten_kich_ban': 'Kịch bản tư vấn tự động Charm Spa',
                'trang_thai': 'Đang hoạt động'
            }
        )

    khach_hang = None
    if user.is_authenticated and hasattr(user, 'khachhang'):
        khach_hang = user.khachhang

    phien, created = PhienHoiThoai.objects.get_or_create(
        ma_pht=session_key,
        defaults={
            'ma_kh': khach_hang,
            'ma_kb': kich_ban_default,
            'trang_thai': 'Đang xử lý'
        }
    )

    if not created and khach_hang and not phien.ma_kh:
        phien.ma_kh = khach_hang
        phien.save()

    return phien


@csrf_exempt
def chatbot_reply(request):
    """API tiếp nhận và xử lý tin nhắn động & gửi Yêu cầu tư vấn (UC-6.1 -> UC-6.7)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            option_type = data.get('type', '')
            session_id = str(data.get('session_id', 'PHT001'))[:10]

            phien = get_or_create_session(session_id, request.user)

            if user_message:
                TinNhan.objects.create(
                    ma_tn=f"TN{uuid.uuid4().hex[:8].upper()}",
                    ma_pht=phien,
                    loai_nguoi_gui='Khách hàng',
                    noi_dung=user_message
                )

            if option_type == 'submit_tu_van':
                fullname = data.get('fullname', '').strip()
                email = data.get('email', '').strip()
                phone = data.get('phone', '').strip()
                topic = data.get('topic', 'Tư vấn chung').strip()

                content_detail = f"Họ tên: {fullname} | SĐT: {phone} | Email: {email} | Nhu cầu: {topic}"

                YeuCauTuVan.objects.create(
                    ma_pht=phien,
                    ma_yctv=f"YC{uuid.uuid4().hex[:8].upper()}",
                    noi_dung=content_detail,
                    trang_thai='Chờ xử lý'
                )

                phien.trang_thai = 'Chờ xử lý'
                phien.save()

                bot_reply = (
                    f"Dạ, yêu cầu tư vấn về <strong>{topic}</strong> của quý khách đã được chuyển tới bộ phận CSKH.<br>"
                    f"Nhân viên tư vấn của Charm Grand Spa sẽ phản hồi trực tiếp ngay tại đây!"
                )

                TinNhan.objects.create(
                    ma_tn=f"TN{uuid.uuid4().hex[:8].upper()}",
                    ma_pht=phien,
                    loai_nguoi_gui='Chatbot',
                    noi_dung=bot_reply
                )

                return JsonResponse({
                    'reply': bot_reply,
                    'status': 'success',
                    'session_status': phien.trang_thai
                })

            if phien.trang_thai in ['Chờ xử lý', 'Đang xử lý'] and option_type != 'tu_van':
                return JsonResponse({'reply': None, 'status': 'success', 'session_status': phien.trang_thai})

            msg_lower = user_message.lower()
            bot_reply = ""

            if option_type == 'tu_van' or 'gặp nhân viên' in msg_lower:
                YeuCauTuVan.objects.get_or_create(
                    ma_pht=phien,
                    defaults={
                        'ma_yctv': f"YC{uuid.uuid4().hex[:8].upper()}",
                        'noi_dung': f"Khách yêu cầu tư vấn: {user_message}",
                        'trang_thai': 'Chờ xử lý'
                    }
                )
                phien.trang_thai = 'Chờ xử lý'
                phien.save()
                bot_reply = "Dạ, yêu cầu của bạn đã được chuyển tới Nhân viên CSKH. Nhân viên tư vấn của Charm Grand Spa sẽ phản hồi trực tiếp ngay tại đây!"

            elif option_type == 'dichvu' or 'dịch vụ' in msg_lower:
                if DichVu and DichVu.objects.exists():
                    dich_vus = DichVu.objects.all()[:5]
                    items = "".join(
                        [f"• <strong>{dv.ten_dich_vu}</strong> - {getattr(dv, 'gia', 'Liên hệ')}đ<br>" for dv in dich_vus]
                    )
                    bot_reply = f"Charm Grand Spa xin gửi bạn danh sách các dịch vụ nổi bật:<br>{items}"
                else:
                    bot_reply = "Charm Grand Spa cung cấp các dịch vụ cao cấp:<br>• <strong>Massage Body Thư Giãn</strong><br>• <strong>Chăm Sóc Da Mặt Chuyên Sâu</strong><br>• <strong>Gội Đầu Dưỡng Sinh</strong>"

            else:
                buoc_kb = BuocChatbot.objects.filter(
                    ma_kb=phien.ma_kb,
                    trang_thai='Đang hoạt động'
                ).order_by('thu_tu').first()

                if buoc_kb:
                    bot_reply = buoc_kb.noi_dung
                else:
                    bot_reply = "Cảm ơn bạn đã nhắn tin. Bạn cần Charm Grand Spa tư vấn dịch vụ hay đặt lịch liệu trình nào ạ?"

            TinNhan.objects.create(
                ma_tn=f"TN{uuid.uuid4().hex[:8].upper()}",
                ma_pht=phien,
                loai_nguoi_gui='Chatbot',
                noi_dung=bot_reply
            )

            return JsonResponse({'reply': bot_reply, 'status': 'success', 'session_status': phien.trang_thai})

        except Exception as e:
            return JsonResponse({'reply': 'Hệ thống đang xử lý, vui lòng thử lại.', 'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid method'}, status=400)


@csrf_exempt
def chat_history(request):
    """API lấy lịch sử hội thoại cho Widget Chat & Staff Dashboard (UC-6.6)"""
    session_id = str(request.GET.get('session_id', ''))[:10]
    if not session_id:
        return JsonResponse({'messages': []})

    tin_nhans = TinNhan.objects.filter(ma_pht__ma_pht=session_id).order_by('thoi_gian')
    data = [{
        'sender': tn.loai_nguoi_gui,
        'content': tn.noi_dung,
        'time': tn.thoi_gian.strftime('%H:%M')
    } for tn in tin_nhans]

    return JsonResponse({'messages': data})


# --- CÁC HÀM QUẢN LÝ DÀNH CHO NHÂN VIÊN CSKH ---

def staff_chat_dashboard(request):
    """Giao diện bảng điều khiển nhân viên (UC-6.8)"""
    yeu_caus = YeuCauTuVan.objects.select_related('ma_pht').order_by('-thoi_gian_yeu_cau')
    return render(request, 'chatbot/staff_chat.html', {'yeu_caus': yeu_caus})


@csrf_exempt
def staff_get_sessions(request):
    """API lấy danh sách các phiên chờ tư vấn kèm bóc tách thông tin khách hàng (UC-6.8)"""
    yeu_caus = YeuCauTuVan.objects.select_related('ma_pht', 'ma_pht__ma_kh').order_by('-thoi_gian_yeu_cau')
    data = []

    for yc in yeu_caus:
        raw_text = yc.noi_dung or ""
        info = {
            'fullname': 'Khách vãng lai',
            'phone': 'Chưa cung cấp',
            'email': 'Chưa cung cấp',
            'topic': 'Tư vấn chung'
        }

        if '|' in raw_text:
            parts = raw_text.split('|')
            for part in parts:
                if 'Họ tên:' in part:
                    info['fullname'] = part.replace('Họ tên:', '').strip()
                elif 'SĐT:' in part:
                    info['phone'] = part.replace('SĐT:', '').strip()
                elif 'Email:' in part:
                    info['email'] = part.replace('Email:', '').strip()
                elif 'Nhu cầu:' in part:
                    info['topic'] = part.replace('Nhu cầu:', '').strip()
        else:
            info['topic'] = raw_text.replace('Khách yêu cầu tư vấn:', '').strip()

        if yc.ma_pht.ma_kh:
            kh = yc.ma_pht.ma_kh
            if hasattr(kh, 'ho_ten') and kh.ho_ten:
                info['fullname'] = kh.ho_ten
            if hasattr(kh, 'so_dien_thoai') and kh.so_dien_thoai:
                info['phone'] = kh.so_dien_thoai

        data.append({
            'ma_pht': yc.ma_pht.ma_pht,
            'noi_dung_raw': yc.noi_dung,
            'fullname': info['fullname'],
            'phone': info['phone'],
            'email': info['email'],
            'topic': info['topic'],
            'trang_thai': yc.trang_thai,
            'thoi_gian': yc.thoi_gian_yeu_cau.strftime('%H:%M %d/%m')
        })

    return JsonResponse({'sessions': data})


@csrf_exempt
def staff_send_reply(request):
    """API Nhân viên gửi tin nhắn trực tiếp (UC-6.9)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_id = str(data.get('session_id', '')).strip()[:10]
            reply_text = data.get('message', '').strip()

            if session_id and reply_text:
                phien = PhienHoiThoai.objects.get(ma_pht=session_id)

                TinNhan.objects.create(
                    ma_tn=f"TN{uuid.uuid4().hex[:8].upper()}",
                    ma_pht=phien,
                    loai_nguoi_gui='Nhân viên',
                    noi_dung=reply_text
                )

                phien.trang_thai = 'Đang xử lý'
                phien.save()
                YeuCauTuVan.objects.filter(ma_pht=phien).update(trang_thai='Đang xử lý')

                return JsonResponse({'status': 'success', 'message': 'Đã gửi phản hồi'})
            else:
                return JsonResponse({'error': 'Thiếu mã phiên hoặc nội dung tin nhắn'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)


def customer_chat_history(request):
    """View hiển thị trang Lịch sử hội thoại đầy đủ cho Khách hàng (UC-6.6)"""
    if not request.user.is_authenticated:
        return redirect('/customer/profile/')

    khach_hang = getattr(request.user, 'khachhang', None)

    if khach_hang:
        phien_list = PhienHoiThoai.objects.filter(ma_kh=khach_hang).order_by('-pk')
    else:
        phien_list = PhienHoiThoai.objects.none()

    selected_session_id = request.GET.get('session_id')
    selected_phien = None
    tin_nhans = []

    if selected_session_id:
        selected_phien = phien_list.filter(ma_pht=selected_session_id).first()

    if not selected_phien and phien_list.exists():
        selected_phien = phien_list.first()

    if selected_phien:
        tin_nhans = TinNhan.objects.filter(ma_pht=selected_phien).order_by('thoi_gian')

    context = {
        'phien_list': phien_list,
        'selected_phien': selected_phien,
        'tin_nhans': tin_nhans,
    }
    return render(request, 'chatbot/customer_history.html', context)


# --- CÁC HÀM QUẢN LÝ HỘI THOẠI ADMIN / CSKH THEO THIẾT KẾ BÁO CÁO ---

def admin_conversation_list(request):
    """Trang danh sách quản lý hội thoại Admin/CSKH (Báo cáo - Ảnh 2)"""
    conversations = PhienHoiThoai.objects.all().order_by('-pk')

    for item in conversations:
        last_msg = TinNhan.objects.filter(ma_pht=item).order_by('-thoi_gian').first()
        item.tin_nhan_cuoi = last_msg.noi_dung if last_msg else "Chưa có tin nhắn"

        yctv = YeuCauTuVan.objects.filter(ma_pht=item).first()
        if yctv and '|' in yctv.noi_dung:
            parts = yctv.noi_dung.split('|')
            for part in parts:
                if 'Họ tên:' in part:
                    item.ten_khach_hang = part.replace('Họ tên:', '').strip()
        else:
            item.ten_khach_hang = getattr(item.ma_kh, 'ho_ten', 'Khách vãng lai') if item.ma_kh else 'Khách vãng lai'

    stats = {
        'total': conversations.count(),
        'cho_xu_ly': PhienHoiThoai.objects.filter(trang_thai='Chờ xử lý').count(),
        'dang_xu_ly': PhienHoiThoai.objects.filter(trang_thai='Đang xử lý').count(),
        'da_hoan_tat': PhienHoiThoai.objects.filter(trang_thai='Đã hoàn tất').count(),
    }

    context = {
        'conversations': conversations,
        'stats': stats,
    }
    return render(request, 'chatbot/admin_conversation_list.html', context)


def admin_conversation_detail(request, session_id):
    """Trang chi tiết hội thoại Admin/CSKH và gửi phản hồi trực tiếp"""
    conversation = get_object_or_404(PhienHoiThoai, ma_pht=session_id)

    if request.method == 'POST':
        reply_text = request.POST.get('message_text', '').strip()
        if reply_text:
            TinNhan.objects.create(
                ma_tn=f"TN{uuid.uuid4().hex[:8].upper()}",
                ma_pht=conversation,
                loai_nguoi_gui='Nhân viên',
                noi_dung=reply_text
            )
            conversation.trang_thai = 'Đang xử lý'
            conversation.save()
            YeuCauTuVan.objects.filter(ma_pht=conversation).update(trang_thai='Đang xử lý')
            messages.success(request, 'Đã gửi phản hồi thành công!')
            return redirect('chatbot:admin_conversation_detail', session_id=session_id)

    messages_list = TinNhan.objects.filter(ma_pht=conversation).order_by('thoi_gian')

    # Khởi tạo thông tin mặc định
    customer_info = {
        'fullname': getattr(conversation.ma_kh, 'ho_ten', 'Khách vãng lai') if conversation.ma_kh else 'Khách vãng lai',
        'phone': getattr(conversation.ma_kh, 'so_dien_thoai', 'Chưa cung cấp') if conversation.ma_kh else 'Chưa cung cấp',
        'email': 'Chưa cung cấp',
        'topic': 'Tư vấn chung'
    }

    # Lấy bản ghi Yêu cầu tư vấn mới nhất từ CSDL để bóc tách thông tin
    yctv = YeuCauTuVan.objects.filter(ma_pht=conversation).order_by('-thoi_gian_yeu_cau').first()
    if yctv and yctv.noi_dung:
        if '|' in yctv.noi_dung:
            parts = yctv.noi_dung.split('|')
            for part in parts:
                if 'Họ tên:' in part:
                    customer_info['fullname'] = part.replace('Họ tên:', '').strip()
                elif 'SĐT:' in part:
                    customer_info['phone'] = part.replace('SĐT:', '').strip()
                elif 'Email:' in part:
                    customer_info['email'] = part.replace('Email:', '').strip()
                elif 'Nhu cầu:' in part:
                    customer_info['topic'] = part.replace('Nhu cầu:', '').strip()
        else:
            customer_info['topic'] = yctv.noi_dung.replace('Khách yêu cầu tư vấn:', '').strip()

    context = {
        'conversation': conversation,
        'messages_list': messages_list,
        'customer_info': customer_info,
    }
    return render(request, 'chatbot/admin_conversation_detail.html', context)


def admin_conversation_complete(request, session_id):
    """Xử lý xác nhận Hoàn tất hội thoại từ Modal Popup (Báo cáo - Ảnh 4)"""
    if request.method == 'POST':
        conversation = get_object_or_404(PhienHoiThoai, ma_pht=session_id)
        ghi_chu = request.POST.get('ghi_chu_xu_ly', '').strip()

        conversation.trang_thai = 'Đã hoàn tất'
        if hasattr(conversation, 'ghi_chu'):
            conversation.ghi_chu = ghi_chu
        conversation.save()

        YeuCauTuVan.objects.filter(ma_pht=conversation).update(trang_thai='Đã hoàn tất')
        messages.success(request, 'Hội thoại đã được đánh dấu Hoàn tất!')
        return redirect('chatbot:admin_conversation_detail', session_id=session_id)

    return redirect('chatbot:admin_conversation_list')


# --- QUẢN LÝ KỊCH BẢN CHATBOT ---

def admin_script_list(request):
    """1. Màn hình Danh sách Kịch bản Chatbot (Ảnh 13) - Đã sửa lỗi FieldError"""
    # Sửa từ -thoi_gian_tao sang -pk vì model KichBanChatbot dùng khóa chính thay vì trường thời gian
    scripts = KichBanChatbot.objects.all().order_by('-pk')
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')

    if status_filter:
        scripts = scripts.filter(trang_thai=status_filter)
    if search_query:
        scripts = scripts.filter(ten_kich_ban__icontains=search_query)

    context = {
        'scripts': scripts,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'chatbot/admin_script_list.html', context)


def admin_script_create(request):
    """Tạo kịch bản mới"""
    if request.method == 'POST':
        ten_kb = request.POST.get('ten_kich_ban')
        mo_ta = request.POST.get('mo_ta', '')
        ma_kb = f"KB{uuid.uuid4().hex[:6].upper()}"

        script = KichBanChatbot.objects.create(
            ma_kb=ma_kb,
            ten_kich_ban=ten_kb,
            mo_ta=mo_ta,
            trang_thai='Đang hoạt động'
        )

        BuocChatbot.objects.create(
            ma_kb=script,
            thu_tu=1,
            ten_buoc="Chào mừng",
            noi_dung="Lắng nghe bạn, chăm sóc tận tâm. Xin chào, bạn muốn tìm hiểu gì?",
            trang_thai='Đang hoạt động'
        )
        messages.success(request, 'Tạo kịch bản thành công!')
        return redirect('chatbot:admin_script_edit', pk=script.pk)

    return redirect('chatbot:admin_script_list')


def admin_script_detail(request, pk):
    """2. Màn hình Chi tiết Luồng Kịch bản (Ảnh 14)"""
    script = get_object_or_404(KichBanChatbot, pk=pk)
    steps = BuocChatbot.objects.filter(ma_kb=script).order_by('thu_tu')

    context = {
        'script': script,
        'steps': steps,
    }
    return render(request, 'chatbot/admin_script_detail.html', context)


def admin_script_edit(request, pk):
    """3. Màn hình Chỉnh sửa / Flow Builder Kịch bản (Ảnh 15)"""
    script = get_object_or_404(KichBanChatbot, pk=pk)
    steps = BuocChatbot.objects.filter(ma_kb=script).order_by('thu_tu')

    if request.method == 'POST':
        script.ten_kich_ban = request.POST.get('ten_kich_ban', script.ten_kich_ban)
        script.mo_ta = request.POST.get('mo_ta', script.mo_ta)
        script.save()

        for step in steps:
            content_key = f"step_content_{step.pk}"
            if content_key in request.POST:
                step.noi_dung = request.POST.get(content_key)
                step.save()

        messages.success(request, 'Đã lưu thay đổi kịch bản!')
        return redirect('chatbot:admin_script_detail', pk=script.pk)

    context = {
        'script': script,
        'steps': steps,
    }
    return render(request, 'chatbot/admin_script_edit.html', context)


def admin_script_preview(request, pk):
    """4. Màn hình Xem trước Kịch bản (Ảnh 17)"""
    script = get_object_or_404(KichBanChatbot, pk=pk)
    steps = BuocChatbot.objects.filter(ma_kb=script).order_by('thu_tu')

    context = {
        'script': script,
        'first_step': steps.first(),
        'steps': steps,
    }
    return render(request, 'chatbot/admin_script_preview.html', context)


def admin_script_delete(request, pk):
    """5. Xác nhận & Thực hiện Xóa Kịch bản (Ảnh 16)"""
    if request.method == 'POST':
        script = get_object_or_404(KichBanChatbot, pk=pk)
        script.delete()
        messages.success(request, 'Đã xóa kịch bản thành công!')
    return redirect('chatbot:admin_script_list')


def admin_script_toggle_status(request, pk):
    """Bật / Tắt trạng thái kịch bản"""
    script = get_object_or_404(KichBanChatbot, pk=pk)
    if script.trang_thai == 'Đang hoạt động':
        script.trang_thai = 'Tạm ngừng'
    else:
        script.trang_thai = 'Đang hoạt động'
    script.save()
    return redirect('chatbot:admin_script_list')



def get_conversation_messages_api(request, session_id):
    """API lấy danh sách tin nhắn mới nhất của phiên hội thoại"""
    try:
        conversation = PhienHoiThoai.objects.get(ma_pht=session_id)
        messages = TinNhan.objects.filter(ma_pht=conversation).order_by('thoi_gian')

        data = []
        for msg in messages:
            data.append({
                'id': msg.ma_tn,
                'sender_type': msg.loai_nguoi_gui,
                'content': msg.noi_dung,
                'timestamp': msg.thoi_gian.strftime('%H:%M') if msg.thoi_gian else ''
            })
        return JsonResponse({'status': 'success', 'messages': data})
    except PhienHoiThoai.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Không tìm thấy hội thoại'}, status=404)