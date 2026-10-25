import json
import uuid
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .models import PhienHoiThoai, TinNhan, BuocChatbot, KichBanChatbot, YeuCauTuVan


def get_or_create_session(session_id, user):
    """Khởi tạo phiên hội thoại an toàn không bao giờ văng lỗi CSDL"""
    session_key = str(session_id)[:10]

    # Tự động tạo kịch bản mặc định nếu CSDL chưa có kịch bản nào
    kich_ban_default = KichBanChatbot.objects.filter(trang_thai='Đang hoạt động').first()
    if not kich_ban_default:
        kich_ban_default, _ = KichBanChatbot.objects.get_or_create(
            ma_kb="KB001",
            defaults={
                'ten_kich_ban': 'Kịch bản tư vấn mặc định',
                'trang_thai': 'Đang hoạt động'
            }
        )

    khach_hang = None
    if user.is_authenticated and hasattr(user, 'khachhang'):
        khach_hang = user.khachhang

    phien, _ = PhienHoiThoai.objects.get_or_create(
        ma_pht=session_key,
        defaults={
            'ma_kh': khach_hang,
            'ma_kb': kich_ban_default,
            'trang_thai': 'Đang xử lý'
        }
    )
    return phien


@csrf_exempt
def chatbot_reply(request):
    """API tiếp nhận tin nhắn từ Khách hàng (UC-6.1 -> UC-6.5)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            option_type = data.get('type', '')
            session_id = str(data.get('session_id', 'PHT001'))[:10]

            phien = get_or_create_session(session_id, request.user)

            # 1. Lưu tin nhắn từ phía Khách hàng vào CSDL
            TinNhan.objects.create(
                ma_tn=f"TN{uuid.uuid4().hex[:8].upper()}",
                ma_pht=phien,
                loai_nguoi_gui='Khách hàng',
                noi_dung=user_message
            )

            # --- KIỂM TRA NẾU PHIÊN ĐÃ CHUYỂN CHO CSKH (Chờ xử lý / Đang xử lý) ---
            # Nếu đã thuộc về nhân viên CSKH và không phải lần đầu bấm 'tu_van', Chatbot giữ yên lặng
            if phien.trang_thai in ['Chờ xử lý', 'Đang xử lý'] and option_type != 'tu_van':
                return JsonResponse({'reply': None, 'status': 'success', 'session_status': phien.trang_thai})

            msg_lower = user_message.lower()

            # 2. Xử lý kịch bản Yêu cầu tư vấn (UC-6.5) - Chuyển giao sang CSKH
            if option_type == 'tu_van' or 'tư vấn' in msg_lower or 'gặp nhân viên' in msg_lower:
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
                bot_reply = "Dạ, yêu cầu của bạn đã được chuyển tới Nhân viên CSKH. Nhân viên tư vấn của Charm Grand Spa sẽ phản hồi trực tiếp ngay tại khung chat này!"

            elif option_type == 'dichvu' or 'dịch vụ' in msg_lower:
                bot_reply = "Charm Grand Spa xin giới thiệu các dịch vụ nổi bật:<br>• <strong>Massage Body Thư Giãn</strong><br>• <strong>Chăm Sóc Da Mặt Chuyên Sâu</strong><br>• <strong>Liệu Trình Toàn Thân</strong>"
            elif option_type == 'gia' or 'giá' in msg_lower:
                bot_reply = "Bảng giá dịch vụ dao động từ 250.000đ - 1.200.000đ. Bạn có thể chọn 'Yêu cầu tư vấn' để nhận báo giá chi tiết."
            elif option_type == 'khuyenmai' or 'khuyến mãi' in msg_lower:
                bot_reply = "🎁 <strong>Ưu đãi tháng này:</strong> Giảm 20% khi đặt lịch trực tuyến trước 24h!"
            else:
                buoc_reply = BuocChatbot.objects.filter(ma_kb=phien.ma_kb, trang_thai='Đang hoạt động').order_by('thu_tu').first()
                bot_reply = buoc_reply.noi_dung if buoc_reply else "Cảm ơn bạn đã nhắn tin cho Charm Grand Spa!"

            # 3. Lưu phản hồi của Chatbot
            TinNhan.objects.create(
                ma_tn=f"TN{uuid.uuid4().hex[:8].upper()}",
                ma_pht=phien,
                loai_nguoi_gui='Chatbot',
                noi_dung=bot_reply
            )

            return JsonResponse({'reply': bot_reply, 'status': 'success', 'session_status': phien.trang_thai})

        except Exception as e:
            return JsonResponse({'reply': 'Đã có lỗi xảy ra.', 'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid method'}, status=400)


@csrf_exempt
def chat_history(request):
    """API lấy lịch sử tin nhắn của một phiên (UC-6.6)"""
    session_id = request.GET.get('session_id', '')
    if not session_id:
        return JsonResponse({'messages': []})

    tin_nhans = TinNhan.objects.filter(ma_pht__ma_pht=session_id).order_by('thoi_gian')
    data = [{
        'sender': tn.loai_nguoi_gui,
        'content': tn.noi_dung,
        'time': tn.thoi_gian.strftime('%H:%M')
    } for tn in tin_nhans]

    return JsonResponse({'messages': data})


# --- LIVE CHAT DASHBOARD DÀNH CHO NHÂN VIÊN CSKH ---

def staff_chat_dashboard(request):
    """Giao diện Bảng điều khiển Live Chat dành cho Nhân viên CSKH (UC-6.8)"""
    yeu_caus = YeuCauTuVan.objects.select_related('ma_pht').order_by('-thoi_gian_yeu_cau')
    return render(request, 'chatbot/staff_chat.html', {'yeu_caus': yeu_caus})


@csrf_exempt
def staff_send_reply(request):
    """API Nhân viên gửi tin nhắn trực tiếp cho Khách hàng (UC-6.9)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            reply_text = data.get('message', '').strip()

            if session_id and reply_text:
                phien = PhienHoiThoai.objects.get(ma_pht=session_id)

                # Lưu tin nhắn với tư cách Nhân viên
                TinNhan.objects.create(
                    ma_tn=f"TN{uuid.uuid4().hex[:8].upper()}",
                    ma_pht=phien,
                    loai_nguoi_gui='Nhân viên',
                    noi_dung=reply_text
                )

                # Cập nhật trạng thái
                phien.trang_thai = 'Đang xử lý'
                phien.save()

                YeuCauTuVan.objects.filter(ma_pht=phien).update(trang_thai='Đang xử lý')

                return JsonResponse({'status': 'success', 'message': 'Đã gửi phản hồi'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def staff_get_sessions(request):
    """API lấy danh sách các yêu cầu tư vấn mới nhất cho nhân viên"""
    yeu_caus = YeuCauTuVan.objects.select_related('ma_pht').order_by('-thoi_gian_yeu_cau')
    data = [{
        'ma_pht': yc.ma_pht.ma_pht,
        'noi_dung': yc.noi_dung,
        'trang_thai': yc.trang_thai,
        'thoi_gian': yc.thoi_gian_yeu_cau.strftime('%H:%M %d/%m')
    } for yc in yeu_caus]
    return JsonResponse({'sessions': data})