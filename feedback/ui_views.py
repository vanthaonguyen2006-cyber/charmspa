import uuid

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import (
    PhanHoiKhieuNai,
    PhanCongXuLy,
    LichSuXuLy,
    TepDinhKem,
)
from accounts.models import TaiKhoan, NhanVien


# Tạo mã duy nhất cho bản ghi phân công và lịch sử xử lý
def _tao_ma(prefix):
    return f"{prefix}{uuid.uuid4().hex[:12].upper()}"


# Kiểm tra đăng nhập và quyền truy cập trang admin/nhân viên
def _kiem_tra_quyen(request, vai_tro):
    if not request.user.is_authenticated:
        return redirect("dang_nhap")

    # Admin là superuser; nhân viên là tài khoản is_staff không phải superuser
    if vai_tro == "admin":
        co_quyen = request.user.is_superuser
    else:
        co_quyen = (
            request.user.is_staff
            and not request.user.is_superuser
        )

    if not co_quyen:
        return HttpResponseForbidden("Bạn không có quyền truy cập trang này.")

    return None


# Lấy tài khoản nghiệp vụ liên kết với tài khoản Django đang đăng nhập
def _tai_khoan_hien_tai(request):
    return TaiKhoan.objects.filter(user=request.user).first()


# Lấy hồ sơ nhân viên và lưu mã nhân viên vào session
def _nhan_vien_hien_tai(request):
    nhan_vien = NhanVien.objects.filter(
        ma_tk__user=request.user
    ).select_related("ma_tk__user").first()

    if nhan_vien:
        request.session["ma_nv"] = nhan_vien.ma_nv

    return nhan_vien


# Lấy thông tin cho sidebar và header trong staff_base.html
def _layout_context(request, is_admin):
    nhan_vien = None if is_admin else _nhan_vien_hien_tai(request)

    if nhan_vien:
        ten_hien_thi = nhan_vien.ho_ten
        vi_tri = nhan_vien.vi_tri
    else:
        ten_hien_thi = (
            request.user.get_full_name()
            or request.user.get_username()
        )
        vi_tri = "Quản trị viên" if is_admin else "Nhân viên CSKH"

    # Tạo chữ viết tắt hiển thị trong avatar
    initials = "".join(
        tu[0] for tu in ten_hien_thi.split() if tu
    )[:2].upper()

    # Đếm tổng phiếu admin hoặc số phiếu thuộc nhân viên đang đăng nhập
    if is_admin:
        feedback_count = PhanHoiKhieuNai.objects.count()
    elif nhan_vien:
        ma_ph = _ma_ph_nhan_vien(nhan_vien.ma_nv)
        feedback_count = PhanHoiKhieuNai.objects.filter(
            ma_ph__in=ma_ph
        ).count()
    else:
        feedback_count = 0

    return {
        "is_admin": is_admin,
        "active_menu": "feedback",
        "staff_name": ten_hien_thi,
        "staff_initials": initials or "?",
        "staff_position": vi_tri,
        "feedback_count": feedback_count,
    }


# Xác định nhân viên hiện đang phụ trách từng phiếu
def _phan_cong_moi_nhat(ma_ph_list=None):
    phan_cong = PhanCongXuLy.objects.order_by("-thoi_gian_pc")

    # Chỉ lấy phân công của những phiếu cần hiển thị nếu đã truyền danh sách
    if ma_ph_list is not None:
        phan_cong = phan_cong.filter(ma_ph_id__in=ma_ph_list)

    ket_qua = {}

    # Giữ bản ghi phân công mới nhất của mỗi phiếu
    for pc in phan_cong.values(
        "ma_ph_id",
        "ma_nv_id",
        "thoi_gian_pc",
        "thoi_gian_ket_thuc",
    ):
        ket_qua.setdefault(pc["ma_ph_id"], pc)

    return ket_qua


# Lấy danh sách mã phiếu do một nhân viên phụ trách theo lần phân công mới nhất
def _ma_ph_nhan_vien(ma_nv):
    if not ma_nv:
        return []

    ds_phan_cong = _phan_cong_moi_nhat()

    return [
        ma_ph for ma_ph, pc in ds_phan_cong.items()
        if pc["ma_nv_id"] == ma_nv
    ]


# Lọc danh sách phản hồi theo từ khóa, trạng thái, loại và ngày gửi
def _loc_phan_hoi(request, mode="all", ma_nv=None):
    phan_hoi = PhanHoiKhieuNai.objects.all().order_by("-ngay_gui")

    tu_khoa = request.GET.get("q", "").strip()
    loai = request.GET.get("type", "")
    trang_thai = request.GET.get("status", "")
    tinh_hop_le = request.GET.get("validity", "")

    # Tìm theo mã phiếu, mã khách hàng, tiêu đề hoặc nội dung
    if tu_khoa:
        phan_hoi = phan_hoi.filter(
            Q(ma_ph__icontains=tu_khoa)
            | Q(ma_kh_id__icontains=tu_khoa)
            | Q(tieu_de__icontains=tu_khoa)
            | Q(noi_dung__icontains=tu_khoa)
        )

    # Lọc theo loại phiếu và trạng thái
    if loai:
        phan_hoi = phan_hoi.filter(loai_ph=loai)

    if trang_thai:
        phan_hoi = phan_hoi.filter(trang_thai_xu_ly=trang_thai)

    if tinh_hop_le:
        phan_hoi = phan_hoi.filter(tinh_hop_le=tinh_hop_le)

    # Lọc theo khoảng thời gian gửi
    ngay_bat_dau = parse_date(request.GET.get("from_date", ""))
    ngay_ket_thuc = parse_date(request.GET.get("to_date", ""))

    if ngay_bat_dau:
        phan_hoi = phan_hoi.filter(ngay_gui__date__gte=ngay_bat_dau)

    if ngay_ket_thuc:
        phan_hoi = phan_hoi.filter(ngay_gui__date__lte=ngay_ket_thuc)

    # Lấy các phiếu đã từng được phân công
    ma_ph_da_phan_cong = PhanCongXuLy.objects.values_list(
        "ma_ph_id", flat=True
    )

    if mode == "unassigned":
        # Chỉ hiển thị phiếu chưa từng được phân công
        phan_hoi = phan_hoi.exclude(ma_ph__in=ma_ph_da_phan_cong)

    elif mode == "invalid":
        # Chỉ hiển thị phiếu bị đánh dấu không hợp lệ
        phan_hoi = phan_hoi.filter(tinh_hop_le="Không hợp lệ")

    elif mode in ("staff", "resolved"):
        # Nhân viên chỉ xem các phiếu được giao cho mình
        phan_hoi = phan_hoi.filter(
            ma_ph__in=_ma_ph_nhan_vien(ma_nv)
        )

        if mode == "resolved":
            phan_hoi = phan_hoi.filter(
                trang_thai_xu_ly="Đã giải quyết"
            )
        else:
            phan_hoi = phan_hoi.filter(tinh_hop_le="Hợp lệ")

    return phan_hoi


# Gắn thông tin phân công mới nhất để hiển thị ở bảng danh sách
def _gan_phan_cong(phan_hoi):
    phieu_list = list(phan_hoi)
    ds_phan_cong = _phan_cong_moi_nhat(
        [ph.ma_ph for ph in phieu_list]
    )

    for ph in phieu_list:
        pc = ds_phan_cong.get(ph.ma_ph)

        ph.ma_nv_hien_tai = pc["ma_nv_id"] if pc else None
        ph.thoi_gian_phan_cong = pc["thoi_gian_pc"] if pc else None
        ph.thoi_gian_ket_thuc = pc["thoi_gian_ket_thuc"] if pc else None

    return phieu_list


# Tính số phiếu và tỷ lệ phần trăm theo trạng thái
def _thong_ke_trang_thai(phan_hoi):
    tong_so = phan_hoi.count()

    da_tiep_nhan = phan_hoi.filter(
        trang_thai_xu_ly="Đã tiếp nhận"
    ).count()

    dang_xu_ly = phan_hoi.filter(
        trang_thai_xu_ly="Đang xử lý"
    ).count()

    da_giai_quyet = phan_hoi.filter(
        trang_thai_xu_ly="Đã giải quyết"
    ).count()

    # Tránh chia cho 0 nếu database chưa có phiếu nào
    return {
        "tong_so": tong_so,
        "da_tiep_nhan": da_tiep_nhan,
        "dang_xu_ly": dang_xu_ly,
        "da_giai_quyet": da_giai_quyet,
        "pct_da_tiep_nhan": round(da_tiep_nhan * 100 / tong_so, 1) if tong_so else 0,
        "pct_dang_xu_ly": round(dang_xu_ly * 100 / tong_so, 1) if tong_so else 0,
        "pct_da_giai_quyet": round(da_giai_quyet * 100 / tong_so, 1) if tong_so else 0,
    }


# Ghi lịch sử thao tác của admin hoặc nhân viên
def _ghi_lich_su(ph, tai_khoan, loai_thao_tac, noi_dung=""):
    return LichSuXuLy.objects.create(
        ma_ls=_tao_ma("LS"),
        ma_ph=ph,
        ma_nguoi_thuc_hien=tai_khoan,
        loai_thao_tac=loai_thao_tac,
        noi_dung=noi_dung,
    )


# Hàm dùng chung để dựng danh sách admin và nhân viên
def _danh_sach_view(request, is_admin, mode, title, subtitle):
    # Xác định nhân viên đăng nhập nếu đây là giao diện nhân viên
    nhan_vien = None if is_admin else _nhan_vien_hien_tai(request)
    ma_nv = nhan_vien.ma_nv if nhan_vien else None

    # Lọc phiếu và phân trang mỗi trang tối đa 8 phiếu
    phan_hoi = _loc_phan_hoi(request, mode, ma_nv)
    page_obj = Paginator(phan_hoi, 8).get_page(request.GET.get("page"))

    # Bổ sung mã nhân viên và thời gian giao phiếu cho template
    phieu_tren_trang = _gan_phan_cong(page_obj.object_list)

    # Thống kê toàn bộ phiếu của admin hoặc phiếu được giao cho nhân viên
    if is_admin:
        phan_hoi_thong_ke = PhanHoiKhieuNai.objects.all()
    elif ma_nv:
        phan_hoi_thong_ke = PhanHoiKhieuNai.objects.filter(
            ma_ph__in=_ma_ph_nhan_vien(ma_nv)
        )
    else:
        phan_hoi_thong_ke = PhanHoiKhieuNai.objects.none()

    context = _layout_context(request, is_admin)
    context.update(_thong_ke_trang_thai(phan_hoi_thong_ke))
    context.update({
        "phan_hoi_list": phieu_tren_trang,
        "page_obj": page_obj,
        "page_mode": mode,
        "page_title": title,
        "page_subtitle": subtitle,

        # Giữ lại các giá trị bộ lọc sau khi tìm kiếm
        "keyword": request.GET.get("q", ""),
        "status": request.GET.get("status", ""),
        "feedback_type": request.GET.get("type", ""),
        "validity": request.GET.get("validity", ""),
        "from_date": request.GET.get("from_date", ""),
        "to_date": request.GET.get("to_date", ""),
    })

    return render(request, "feedback/feedback_list.html", context)


# ADMIN: Danh sách tất cả phản hồi và khiếu nại
def admin_feedback_list(request):
    loi = _kiem_tra_quyen(request, "admin")
    if loi:
        return loi

    return _danh_sach_view(
        request, True, "all",
        "Quản lý phản hồi & khiếu nại",
        "Tiếp nhận, phân công và theo dõi chất lượng xử lý ý kiến khách hàng.",
    )


# ADMIN: Danh sách phiếu chưa phân công
def admin_feedback_unassigned(request):
    loi = _kiem_tra_quyen(request, "admin")
    if loi:
        return loi

    return _danh_sach_view(
        request, True, "unassigned",
        "Phiếu chưa phân công",
        "Các phiếu cần được giao cho nhân viên xử lý.",
    )


# ADMIN: Danh sách phiếu không hợp lệ
def admin_feedback_invalid(request):
    loi = _kiem_tra_quyen(request, "admin")
    if loi:
        return loi

    return _danh_sach_view(
        request, True, "invalid",
        "Phiếu không hợp lệ",
        "Theo dõi các phiếu được đánh dấu không hợp lệ.",
    )


# NHÂN VIÊN: Danh sách phiếu được phân công
def staff_feedback_list(request):
    loi = _kiem_tra_quyen(request, "staff")
    if loi:
        return loi

    return _danh_sach_view(
        request, False, "staff",
        "Phiếu được phân công",
        "Ưu tiên các phiếu cần xử lý và cập nhật tiến độ thường xuyên.",
    )


# NHÂN VIÊN: Danh sách phiếu đã giải quyết
def staff_feedback_resolved(request):
    loi = _kiem_tra_quyen(request, "staff")
    if loi:
        return loi

    return _danh_sach_view(
        request, False, "resolved",
        "Phiếu đã giải quyết",
        "Theo dõi các yêu cầu đã hoàn tất xử lý.",
    )

# ADMIN: Xem chi tiết, phân công, đánh dấu không hợp lệ,
# cập nhật trạng thái và hoàn tất phiếu
def admin_feedback_detail(request, feedback_id):
    # Kiểm tra quyền quản trị viên
    loi = _kiem_tra_quyen(request, "admin")
    if loi:
        return loi

    # Lấy phiếu cần xem
    ph = get_object_or_404(
        PhanHoiKhieuNai,
        ma_ph=feedback_id
    )

    if request.method == "POST":
        action = request.POST.get("action", "").strip()



        # ==================================================
        # 1. ADMIN ĐÁNH DẤU PHIẾU KHÔNG HỢP LỆ
        # ==================================================
        if action == "mark_invalid":
            ly_do = request.POST.get(
                "ly_do_khong_hop_le", ""
            )
            chi_tiet = request.POST.get(
                "chi_tiet_ly_do", ""
            ).strip()

            # Lấy các lý do hợp lệ được khai báo trong model
            ly_do_hop_le = {
                value
                for value, label
                in PhanHoiKhieuNai.LY_DO_KHONG_HOP_LE_CHOICES
            }

            if ly_do not in ly_do_hop_le:
                messages.error(
                    request,
                    "Vui lòng chọn lý do không hợp lệ."
                )

            else:
                now = timezone.now()

                with transaction.atomic():
                    # Cập nhật tính hợp lệ và trạng thái phiếu
                    ph.tinh_hop_le = "Không hợp lệ"
                    ph.ly_do_khong_hop_le = ly_do
                    ph.chi_tiet_ly_do = chi_tiet or None

                    # Phiếu không hợp lệ được đóng ngay
                    ph.trang_thai_xu_ly = "Đã giải quyết"
                    ph.ngay_giai_quyet = now

                    ph.save()

                    # Đóng tất cả phân công đang còn hiệu lực
                    PhanCongXuLy.objects.filter(
                        ma_ph=ph,
                        thoi_gian_ket_thuc__isnull=True
                    ).update(
                        thoi_gian_ket_thuc=now
                    )

                    # Ghi lịch sử thao tác của admin
                    noi_dung = (
                        f"Lý do: {ly_do}. "
                        "Phiếu được chuyển sang trạng thái "
                        "'Đã giải quyết' và các phân công đang mở đã được đóng."
                    )

                    if chi_tiet:
                        noi_dung += f" Chi tiết: {chi_tiet}"

                    _ghi_lich_su(
                        ph,
                        tai_khoan,
                        "Đánh dấu không hợp lệ",
                        noi_dung
                    )

                messages.success(
                    request,
                    "Đã đánh dấu phiếu không hợp lệ, "
                    "chuyển sang Đã giải quyết và đóng phân công."
                )

        # ==================================================
        # 2. ADMIN PHÂN CÔNG HOẶC ĐỔI NHÂN VIÊN
        # ==================================================
        elif action == "assign":
            ma_nv = request.POST.get("ma_nv", "").strip()

            # Chỉ cho phép chọn nhân viên tồn tại
            nhan_vien = NhanVien.objects.filter(
                ma_nv=ma_nv
            ).first()

            if not ma_nv or not nhan_vien:
                messages.error(
                    request,
                    "Vui lòng chọn một nhân viên hợp lệ."
                )

            elif ph.tinh_hop_le != "Hợp lệ":
                messages.error(
                    request,
                    "Không thể phân công phiếu không hợp lệ."
                )

            elif ph.trang_thai_xu_ly == "Đã giải quyết":
                messages.error(
                    request,
                    "Phiếu đã giải quyết, không thể phân công lại."
                )

            else:
                now = timezone.now()

                with transaction.atomic():
                    # Đóng phân công trước đó nếu còn hiệu lực
                    PhanCongXuLy.objects.filter(
                        ma_ph=ph,
                        thoi_gian_ket_thuc__isnull=True
                    ).update(
                        thoi_gian_ket_thuc=now
                    )

                    # Tạo phân công mới
                    PhanCongXuLy.objects.create(
                        ma_pc=_tao_ma("PC"),
                        ma_ph=ph,
                        ma_nv=nhan_vien,
                        ma_nguoi_phan_cong=tai_khoan
                    )

                    # Cập nhật trạng thái phiếu
                    ph.trang_thai_xu_ly = "Đang xử lý"
                    ph.save(
                        update_fields=["trang_thai_xu_ly"]
                    )

                    # Ghi lịch sử phân công
                    _ghi_lich_su(
                        ph,
                        tai_khoan,
                        "Phân công",
                        (
                            f"Admin phân công cho {nhan_vien.ho_ten} "
                            f"(mã {nhan_vien.ma_nv})."
                        )
                    )

                messages.success(
                    request,
                    f"Đã phân công phiếu {feedback_id} "
                    f"cho nhân viên {nhan_vien.ho_ten}."
                )

        # ==================================================
        # 3. ADMIN CẬP NHẬT TRẠNG THÁI VÀ GHI CHÚ
        # ==================================================
        elif action == "update":

            # Không cho cập nhật phiếu không hợp lệ hoặc đã đóng
            if ph.tinh_hop_le != "Hợp lệ":
                messages.error(
                    request,
                    "Phiếu không hợp lệ không thể tiếp tục cập nhật."
                )

            elif ph.trang_thai_xu_ly == "Đã giải quyết":
                messages.error(
                    request,
                    "Phiếu đã giải quyết, không thể cập nhật tiếp."
                )

            else:
                trang_thai = request.POST.get(
                    "trang_thai_xu_ly", ""
                )
                ghi_chu = request.POST.get(
                    "noi_dung_xu_ly", ""
                ).strip()

                if trang_thai not in [
                    "Đã tiếp nhận",
                    "Đang xử lý"
                ]:
                    messages.error(
                        request,
                        "Trạng thái cập nhật không hợp lệ."
                    )

                elif not ghi_chu:
                    messages.error(
                        request,
                        "Vui lòng nhập ghi chú xử lý."
                    )

                else:
                    with transaction.atomic():
                        # Cập nhật trạng thái phiếu
                        ph.trang_thai_xu_ly = trang_thai
                        ph.save(
                            update_fields=["trang_thai_xu_ly"]
                        )

                        # Ghi lại ghi chú và người thực hiện
                        _ghi_lich_su(
                            ph,
                            tai_khoan,
                            "Cập nhật trạng thái",
                            (
                                f"Admin cập nhật trạng thái thành "
                                f"'{trang_thai}'. Ghi chú: {ghi_chu}"
                            )
                        )

                    messages.success(
                        request,
                        "Admin đã cập nhật trạng thái và ghi chú xử lý."
                    )

        # ==================================================
        # 4. ADMIN HOÀN TẤT PHIẾU TRỰC TIẾP
        # ==================================================
        elif action == "complete":

            if ph.tinh_hop_le != "Hợp lệ":
                messages.error(
                    request,
                    "Phiếu không hợp lệ đã được đóng, không thể hoàn tất lại."
                )

            elif ph.trang_thai_xu_ly == "Đã giải quyết":
                messages.error(
                    request,
                    "Phiếu này đã được giải quyết trước đó."
                )

            else:
                phan_hoi_cuoi = request.POST.get(
                    "noi_dung_phan_hoi", ""
                ).strip()

                if not phan_hoi_cuoi:
                    messages.error(
                        request,
                        "Vui lòng nhập nội dung phản hồi cuối cùng."
                    )

                else:
                    now = timezone.now()

                    with transaction.atomic():
                        # Chuyển phiếu sang trạng thái đã giải quyết
                        ph.trang_thai_xu_ly = "Đã giải quyết"
                        ph.ngay_giai_quyet = now
                        ph.save()

                        # Đóng tất cả phân công đang còn hiệu lực
                        PhanCongXuLy.objects.filter(
                            ma_ph=ph,
                            thoi_gian_ket_thuc__isnull=True
                        ).update(
                            thoi_gian_ket_thuc=now
                        )

                        # Lưu nội dung phản hồi cuối cùng vào lịch sử
                        _ghi_lich_su(
                            ph,
                            tai_khoan,
                            "Hoàn tất xử lý",
                            (
                                "Admin trực tiếp hoàn tất phiếu. "
                                f"Phản hồi cuối cùng: {phan_hoi_cuoi}"
                            )
                        )

                    messages.success(
                        request,
                        "Admin đã hoàn tất xử lý phiếu."
                    )

        else:
            messages.error(
                request,
                "Thao tác không hợp lệ."
            )

        # Quay lại trang chi tiết sau khi xử lý POST
        return redirect(
            "feedback:admin_feedback_detail",
            feedback_id=feedback_id
        )

    # ==================================================
    # 5. LẤY DỮ LIỆU HIỂN THỊ TRANG CHI TIẾT
    # ==================================================

    # Lịch sử xử lý
    lich_su = LichSuXuLy.objects.filter(
        ma_ph=ph
    ).select_related(
        "ma_nguoi_thuc_hien"
    ).order_by("ngay_thuc_hien")

    # Tệp đính kèm
    tep_dinh_kem = TepDinhKem.objects.filter(
        ma_ph=ph
    )

    # Phân công mới nhất
    phan_cong = PhanCongXuLy.objects.filter(
        ma_ph=ph
    ).select_related(
        "ma_nv"
    ).order_by(
        "-thoi_gian_pc"
    ).first()

    # Danh sách nhân viên
    danh_sach_nhan_vien = NhanVien.objects.all().order_by(
        "ho_ten"
    )

    # Context giao diện
    context = _layout_context(request, True)

    context.update({
        "ph": ph,
        "feedback_id": ph.ma_ph,
        "customer": ph.ma_kh,
        "lich_su": lich_su,
        "tep_dinh_kem": tep_dinh_kem,
        "phan_cong": phan_cong,
        "danh_sach_nhan_vien": danh_sach_nhan_vien,
        "nhan_vien_list": danh_sach_nhan_vien,
        "ly_do_khong_hop_le_choices":
            PhanHoiKhieuNai.LY_DO_KHONG_HOP_LE_CHOICES,
    })

    return render(
        request,
        "feedback/feedback_admin_detail.html",
        context
    )

# NHÂN VIÊN: Xem chi tiết phiếu, cập nhật và hoàn tất xử lý
def staff_feedback_detail(request, feedback_id):
    loi = _kiem_tra_quyen(request, "staff")
    if loi:
        return loi

    # Lấy hồ sơ nhân viên đang đăng nhập
    nhan_vien = _nhan_vien_hien_tai(request)

    if not nhan_vien:
        return HttpResponseForbidden("Tài khoản chưa có hồ sơ nhân viên.")

    # Kiểm tra phiếu có được giao cho nhân viên trong lần phân công gần nhất không
    phan_cong = PhanCongXuLy.objects.filter(
        ma_ph_id=feedback_id,
        ma_nv=nhan_vien,
    ).select_related("ma_ph").order_by("-thoi_gian_pc").first()

    phan_cong_moi_nhat = PhanCongXuLy.objects.filter(
        ma_ph_id=feedback_id
    ).order_by("-thoi_gian_pc").first()

    if (
        not phan_cong
        or not phan_cong_moi_nhat
        or phan_cong_moi_nhat.ma_pc != phan_cong.ma_pc
    ):
        return HttpResponseForbidden("Phiếu này chưa được phân công cho bạn.")

    ph = get_object_or_404(PhanHoiKhieuNai, ma_ph=feedback_id)

    if request.method == "POST":
        action = request.POST.get("action")
        tai_khoan = _tai_khoan_hien_tai(request)

        if not tai_khoan:
            messages.error(request, "Không tìm thấy tài khoản nghiệp vụ của bạn.")
            return redirect(
                "feedback:staff_feedback_detail",
                feedback_id=feedback_id
            )

        # Không cho cập nhật phiếu không hợp lệ hoặc đã hoàn tất
        if ph.tinh_hop_le != "Hợp lệ":
            messages.error(request, "Phiếu này không thuộc quy trình xử lý thông thường.")
        elif (
            ph.trang_thai_xu_ly == "Đã giải quyết"
            or phan_cong.thoi_gian_ket_thuc
        ):
            messages.error(request, "Phiếu này đã hoàn tất xử lý.")

        # Cập nhật trạng thái và ghi chú xử lý
        elif action == "update":
            trang_thai = request.POST.get("trang_thai_xu_ly", "")
            ghi_chu = request.POST.get("noi_dung_xu_ly", "").strip()

            if trang_thai not in ["Đã tiếp nhận", "Đang xử lý"]:
                messages.error(request, "Trạng thái cập nhật không hợp lệ.")
            elif not ghi_chu:
                messages.error(request, "Vui lòng nhập ghi chú xử lý.")
            else:
                with transaction.atomic():
                    ph.trang_thai_xu_ly = trang_thai
                    ph.save()

                    # Ghi nội dung cập nhật vào lịch sử xử lý
                    _ghi_lich_su(
                        ph, tai_khoan,
                        "Cập nhật trạng thái",
                        ghi_chu,
                    )

                messages.success(request, "Đã lưu cập nhật xử lý.")
                return redirect(
                    "feedback:staff_feedback_detail",
                    feedback_id=feedback_id
                )

        # Hoàn tất xử lý và đóng phiếu
        elif action == "complete":
            phan_hoi_cuoi = request.POST.get(
                "noi_dung_phan_hoi", ""
            ).strip()

            if not phan_hoi_cuoi:
                messages.error(request, "Vui lòng nhập phản hồi cuối cùng.")
            else:
                now = timezone.now()

                with transaction.atomic():
                    # Chuyển trạng thái phiếu sang đã giải quyết
                    ph.trang_thai_xu_ly = "Đã giải quyết"
                    ph.ngay_giai_quyet = now
                    ph.save()

                    # Đánh dấu phân công đã hoàn tất
                    PhanCongXuLy.objects.filter(
                        ma_ph=ph,
                        ma_nv=nhan_vien,
                        thoi_gian_ket_thuc__isnull=True,
                    ).update(thoi_gian_ket_thuc=now)

                    # Lưu phản hồi cuối cùng trong lịch sử xử lý
                    _ghi_lich_su(
                        ph, tai_khoan,
                        "Hoàn tất xử lý",
                        phan_hoi_cuoi,
                    )

                messages.success(request, "Đã hoàn tất xử lý phiếu.")
                return redirect(
                    "feedback:staff_feedback_detail",
                    feedback_id=feedback_id
                )

        else:
            messages.error(request, "Thao tác không hợp lệ.")

        return redirect(
            "feedback:staff_feedback_detail",
            feedback_id=feedback_id
        )

    # Lấy lịch sử và tệp đính kèm cho trang chi tiết nhân viên
    lich_su = LichSuXuLy.objects.filter(
        ma_ph=ph
    ).select_related("ma_nguoi_thuc_hien").order_by("ngay_thuc_hien")

    tep_dinh_kem = TepDinhKem.objects.filter(ma_ph=ph)

    context = _layout_context(request, False)
    context.update({
        "ph": ph,
        "nhan_vien": nhan_vien,
        "customer": ph.ma_kh,
        "lich_su": lich_su,
        "tep_dinh_kem": tep_dinh_kem,
        "phan_cong": phan_cong,
    })

    return render(
        request,
        "feedback/feedback_staff_detail.html",
        context
    )


# ADMIN: Thống kê theo loại phiếu và trạng thái xử lý
def admin_feedback_statistics(request):
    loi = _kiem_tra_quyen(request, "admin")
    if loi:
        return loi

    tat_ca = PhanHoiKhieuNai.objects.all()
    tong_so = tat_ca.count()

    # Đếm phản hồi và khiếu nại
    phan_hoi_count = tat_ca.filter(loai_ph="Phản hồi").count()
    khieu_nai_count = tat_ca.filter(loai_ph="Khiếu nại").count()

    # Đếm số phiếu theo trạng thái
    da_tiep_nhan = tat_ca.filter(
        trang_thai_xu_ly="Đã tiếp nhận"
    ).count()
    dang_xu_ly = tat_ca.filter(
        trang_thai_xu_ly="Đang xử lý"
    ).count()
    da_giai_quyet = tat_ca.filter(
        trang_thai_xu_ly="Đã giải quyết"
    ).count()

    # Tính tỷ lệ phần trăm, tránh chia cho 0 khi chưa có dữ liệu
    pct_phan_hoi = round(phan_hoi_count * 100 / tong_so, 1) if tong_so else 0
    pct_khieu_nai = round(khieu_nai_count * 100 / tong_so, 1) if tong_so else 0
    pct_da_tiep_nhan = round(da_tiep_nhan * 100 / tong_so, 1) if tong_so else 0
    pct_dang_xu_ly = round(dang_xu_ly * 100 / tong_so, 1) if tong_so else 0
    pct_da_giai_quyet = round(da_giai_quyet * 100 / tong_so, 1) if tong_so else 0

    # Đưa dữ liệu thống kê sang template
    context = _layout_context(request, True)
    context.update({
        "tong_so": tong_so,
        "phan_hoi_count": phan_hoi_count,
        "khieu_nai_count": khieu_nai_count,
        "da_tiep_nhan": da_tiep_nhan,
        "dang_xu_ly": dang_xu_ly,
        "da_giai_quyet": da_giai_quyet,
        "pct_phan_hoi": pct_phan_hoi,
        "pct_khieu_nai": pct_khieu_nai,
        "pct_da_tiep_nhan": pct_da_tiep_nhan,
        "pct_dang_xu_ly": pct_dang_xu_ly,
        "pct_da_giai_quyet": pct_da_giai_quyet,
    })

    return render(
        request,
        "feedback/feedback_statistics.html",
        context
    )

