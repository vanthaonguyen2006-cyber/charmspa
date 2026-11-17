import os

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from django.db import transaction

from customers.models import KhachHang
from .forms import PhanHoiKhieuNaiForm
from .models import PhanHoiKhieuNai, TepDinhKem
from .models import  LichSuXuLy
from accounts.models import get_user_role, ROLE_CUSTOMER


# ============================================================
# 1. LẤY HỒ SƠ KHÁCH HÀNG ĐANG ĐĂNG NHẬP
# ============================================================

def _get_current_customer(request):
    # Bước 1: Kiểm tra người dùng đã đăng nhập chưa.
    if not request.user.is_authenticated:
        return None

    # Bước 2: Chỉ cho phép tài khoản có role Khách hàng.
    if get_user_role(request.user) != ROLE_CUSTOMER:
        return None

    # Bước 3: Tìm đúng hồ sơ khách hàng thuộc tài khoản đang đăng nhập.
    # Kiểm tra thêm role trong database để tránh lấy nhầm hồ sơ.
    return KhachHang.objects.filter(
        ma_tk__user=request.user,
        ma_tk__vai_tro=ROLE_CUSTOMER
    ).first()


# ============================================================
# 2. TẠO MÃ PHIẾU KHÔNG BỊ TRÙNG
# ============================================================

def _generate_feedback_id():
    # Tạo mã theo dạng PH001, PH002, PH003,...
    number = PhanHoiKhieuNai.objects.count() + 1

    # Nếu mã đã tồn tại thì tăng số cho đến khi tìm được mã trống
    while True:
        feedback_id = f"PH{number:03d}"

        if not PhanHoiKhieuNai.objects.filter(
            ma_ph=feedback_id
        ).exists():
            return feedback_id

        number += 1


# ============================================================
# 3. TẠO MÃ TỆP ĐÍNH KÈM
# ============================================================

def _generate_attachment_id():
    # Tạo mã tệp theo dạng TP001, TP002, TP003,...
    number = TepDinhKem.objects.count() + 1

    while True:
        attachment_id = f"TP{number:03d}"

        if not TepDinhKem.objects.filter(
            ma_tep=attachment_id
        ).exists():
            return attachment_id

        number += 1


# ============================================================
# 4. LƯU TỆP ĐÍNH KÈM VÀO DATABASE
# ============================================================

def _save_attachments(request, phan_hoi):
    # Lấy các tệp gửi lên từ input name="tep_dinh_kem"
    danh_sach_tep = request.FILES.getlist("tep_dinh_kem")

    for tep in danh_sach_tep:
        # Chỉ lấy tên tệp, tránh sử dụng đường dẫn do người dùng gửi lên
        ten_tep = os.path.basename(tep.name)

        # Lưu tệp thật vào thư mục media/feedback_attachments/
        duong_dan = default_storage.save(
            f"feedback_attachments/{ten_tep}",
            tep,
        )

        # Lưu thông tin tệp vào bảng TEP_DINH_KEM
        TepDinhKem.objects.create(
            ma_tep=_generate_attachment_id(),
            ma_ph=phan_hoi,
            ten_tep=ten_tep,
            duong_dan_tep=duong_dan,
            loai_tep=(
                getattr(tep, "content_type", None)
                or os.path.splitext(ten_tep)[1]
                or "Không xác định"
            )[:50],
        )


# ============================================================
# 5. KHÁCH HÀNG: TẠO PHẢN HỒI / KHIẾU NẠI
# ============================================================

def customer_feedback_create(request):
    # Yêu cầu khách hàng đăng nhập trước khi gửi phản hồi
    if not request.user.is_authenticated:
        return redirect("dang_nhap")

    # Lấy popup thành công ngay đầu hàm để không bỏ sót khi render sớm
    success_feedback = request.session.pop("feedback_success", None)

    # Lấy đúng hồ sơ khách hàng liên kết với tài khoản hiện tại
    khach_hang = _get_current_customer(request)

    # Không thêm messages.error mỗi lần tải trang để tránh thông báo bị lặp
    if not khach_hang:
        return render(
            request,
            "feedback/gui_phan_hoi.html",
            {
                "form": PhanHoiKhieuNaiForm(),
                "khach_hang": None,
                "success_feedback": success_feedback,
                "profile_error": (
                    "Tài khoản chưa được liên kết với hồ sơ khách hàng. "
                    "Vui lòng kiểm tra thông tin tài khoản."
                ),
            },
        )

    # Xử lý khi khách hàng gửi biểu mẫu
    if request.method == "POST":
        form = PhanHoiKhieuNaiForm(request.POST, request.FILES)

        if form.is_valid():
            with transaction.atomic():
                # Tạo phiếu mới, chưa lưu ngay
                phan_hoi = form.save(commit=False)

                # Gắn mã phiếu và đúng mã khách hàng đang đăng nhập
                phan_hoi.ma_ph = _generate_feedback_id()
                phan_hoi.ma_kh_id = khach_hang.ma_kh
                phan_hoi.save()

                # Lưu các tệp đính kèm nếu có
                _save_attachments(request, phan_hoi)

            # Lưu thông tin popup vào session, sau đó chuyển hướng
            request.session["feedback_success"] = {
                "ma_ph": phan_hoi.ma_ph,
                "trang_thai": phan_hoi.get_trang_thai_xu_ly_display(),
            }

            return redirect("feedback:customer_feedback_create")

    else:
        # Hiển thị biểu mẫu trống khi mở trang lần đầu
        form = PhanHoiKhieuNaiForm()

    return render(
        request,
        "feedback/gui_phan_hoi.html",
        {
            "form": form,
            "khach_hang": khach_hang,
            "success_feedback": success_feedback,
            "profile_error": None,
        },
    )

# ============================================================
# 6. KHÁCH HÀNG: DANH SÁCH PHẢN HỒI / KHIẾU NẠI
# URL: /feedback/customer/list/
# ============================================================

def customer_feedback_list(request):
    # Yêu cầu đăng nhập để chỉ xem phiếu của khách hàng hiện tại
    if not request.user.is_authenticated:
        return redirect("dang_nhap")

    khach_hang = _get_current_customer(request)

    # Tài khoản chưa có hồ sơ khách hàng liên kết
    if not khach_hang:
        messages.error(
            request,
            "Tài khoản chưa được liên kết với hồ sơ khách hàng."
        )

        return render(
            request,
            "feedback/customer_feedback_list.html",
            {
                "khach_hang": None,
                "danh_sach_phan_hoi": [],
                "phan_hoi_list": [],
                "page_obj": None,
                "total_count": 0,
                "selected_type": "",
                "selected_status": "",
                "loai_ph_choices": PhanHoiKhieuNai.LOAI_PH_CHOICES,
                "trang_thai_choices": PhanHoiKhieuNai.TRANG_THAI_CHOICES,
            }
        )

    # Chỉ lấy các phiếu của khách hàng đang đăng nhập
    danh_sach = PhanHoiKhieuNai.objects.filter(
        ma_kh_id=khach_hang.ma_kh
    ).order_by("-ngay_gui")

    # --------------------------------------------------------
    # LỌC THEO LOẠI PHIẾU
    # --------------------------------------------------------

    # Hỗ trợ cả tên tham số URL cũ và mới
    selected_type = request.GET.get(
        "loai_ph",
        request.GET.get("type", "")
    )

    # Chỉ chấp nhận các loại phiếu đã khai báo trong model
    if selected_type in dict(PhanHoiKhieuNai.LOAI_PH_CHOICES):
        danh_sach = danh_sach.filter(
            loai_ph=selected_type
        )
    else:
        selected_type = ""

    # --------------------------------------------------------
    # LỌC THEO TRẠNG THÁI XỬ LÝ
    # --------------------------------------------------------

    selected_status = request.GET.get(
        "trang_thai",
        request.GET.get("status", "")
    )

    # Chỉ chấp nhận trạng thái đã khai báo trong model
    if selected_status in dict(PhanHoiKhieuNai.TRANG_THAI_CHOICES):
        danh_sach = danh_sach.filter(
            trang_thai_xu_ly=selected_status
        )
    else:
        selected_status = ""

    # Đếm số phiếu sau khi áp dụng các bộ lọc
    total_count = danh_sach.count()

    # --------------------------------------------------------
    # PHÂN TRANG: MỖI TRANG HIỂN THỊ 5 PHIẾU
    # --------------------------------------------------------

    paginator = Paginator(danh_sach, 5)

    # Lấy số trang từ URL, mặc định là trang 1
    page_number = request.GET.get("page", 1)

    # Lấy các phiếu thuộc trang hiện tại
    page_obj = paginator.get_page(page_number)
    phieu_tren_trang = list(page_obj.object_list)

    # Gắn khách hàng đã lấy sẵn để template không phải truy vấn lại
    for phieu in phieu_tren_trang:
        phieu._state.fields_cache["ma_kh"] = khach_hang

    # Trả dữ liệu sang template danh sách
    return render(
        request,
        "feedback/customer_feedback_list.html",
        {
            "khach_hang": khach_hang,

            # Giữ hai tên biến để tương thích template hiện tại
            "danh_sach_phan_hoi": phieu_tren_trang,
            "phan_hoi_list": phieu_tren_trang,

            # Thông tin phân trang
            "page_obj": page_obj,
            "paginator": paginator,

            # Thông tin bộ lọc và tổng số phiếu
            "total_count": total_count,
            "selected_type": selected_type,
            "selected_status": selected_status,

            # Các lựa chọn hiển thị trên dropdown lọc
            "loai_ph_choices": PhanHoiKhieuNai.LOAI_PH_CHOICES,
            "trang_thai_choices": PhanHoiKhieuNai.TRANG_THAI_CHOICES,
        }
    )


# ============================================================
# 7. KHÁCH HÀNG: CHI TIẾT MỘT PHIẾU
# ============================================================


def customer_feedback_detail(request, feedback_id):
    # Yêu cầu khách hàng đăng nhập trước khi xem chi tiết phiếu.
    if not request.user.is_authenticated:
        return redirect("dang_nhap")

    # Lấy hồ sơ khách hàng đang đăng nhập.
    khach_hang = _get_current_customer(request)

    if not khach_hang:
        messages.error(
            request,
            "Tài khoản chưa được liên kết với hồ sơ khách hàng."
        )
        return redirect("feedback:customer_feedback_list")

    # Chỉ cho phép khách hàng xem phiếu thuộc chính tài khoản của mình.
    phan_hoi = get_object_or_404(
        PhanHoiKhieuNai,
        ma_ph=feedback_id,
        ma_kh_id=khach_hang.ma_kh
    )

    # Gắn hồ sơ khách hàng đã lấy sẵn để template có thể sử dụng.
    phan_hoi._state.fields_cache["ma_kh"] = khach_hang

    # Lấy danh sách tệp đính kèm của phiếu.
    tep_dinh_kem = TepDinhKem.objects.filter(
        ma_ph_id=phan_hoi.ma_ph
    )

    # Chỉ lấy những cập nhật đã được Admin hoặc nhân viên
    # cho phép hiển thị công khai cho khách hàng.
    # Không lấy trường noi_dung vì đây là ghi chú nội bộ.
    lich_su_cong_khai = (
        LichSuXuLy.objects.filter(
            ma_ph_id=phan_hoi.ma_ph,
            noi_dung_khach_hang__isnull=False
        )
        .exclude(noi_dung_khach_hang__exact="")
        .order_by("ngay_thuc_hien")
    )

    # Xác định bước tiến độ dựa trên trạng thái hiện tại của phiếu.
    if phan_hoi.trang_thai_xu_ly == "Đã giải quyết":
        status_level = 3
    elif phan_hoi.trang_thai_xu_ly == "Đang xử lý":
        status_level = 2
    else:
        status_level = 1

    # Truyền dữ liệu cần thiết sang giao diện chi tiết khách hàng.
    return render(
        request,
        "feedback/customer_feedback_detail.html",
        {
            "khach_hang": khach_hang,
            "phan_hoi": phan_hoi,
            "tep_dinh_kem": tep_dinh_kem,

            # Chỉ truyền lịch sử có nội dung công khai.
            "lich_su_cong_khai": lich_su_cong_khai,

            # Cấp độ tiến độ để hiển thị thanh 3 bước.
            "status_level": status_level,
        }
    )
