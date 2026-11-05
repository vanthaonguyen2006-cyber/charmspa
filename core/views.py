from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from customers.models import KhachHang
from feedback.models import PhanHoiKhieuNai
from notifications.models import ChuongTrinhUuDai, ThongBao
from django.core.paginator import Paginator
from bookings.models import LichHen
from django.db.models import Avg, Count, Q, Sum
from services.models import DichVu, DichVuDaSuDung
from chatbot.models import YeuCauTuVan

# Trang chủ khách hàng
def customer_home(request):
    return render(request, 'core/customer_home.html')


# Trang chủ nhân viên
def staff_home(request):
    return render(request, 'core/staff_home.html')


# Trang chủ Charm Spa Grand (AMy)
def home(request):
    return render(request, "core/home.html")


# Trang liệu trình (main)
def lieu_trinh_page(request):
    dich_vu_list = list(DichVu.objects.all().order_by('pk'))

    # Sử dụng bộ ảnh dịch vụ hiện có của dự án.
    cards = [
        {
            'service': dv,
            'image': f'images/services/service{(i % 10) + 1}.jpg',
        }
        for i, dv in enumerate(dich_vu_list)
    ]

    page_obj = Paginator(cards, 9).get_page(request.GET.get('page'))

    return render(request, 'core/lieu_trinh.html', {
        'page_obj': page_obj
    })


# Trang hồ sơ khách hàng (main)
@login_required(login_url='/accounts/dang_nhap/')
def customer_profile_view(request):
    # Chỉ lấy hồ sơ thuộc tài khoản đang đăng nhập.
    khach_hang = KhachHang.objects.select_related(
        'ma_tk', 'ma_tv'
    ).filter(
        ma_tk__user=request.user
    ).first()

    return render(request, 'customer/customer_profile.html', {
        'khach_hang': khach_hang
    })


# Trang liên hệ (main)
def contact_view(request):
    return render(request, 'core/contact.html')

# Trang tổng quan Management
def staff_dashboard_view(request):
  now = timezone.now()
  today = now.date()

  # 1. TRUY VẤN KPI TỔNG QUAN
  so_lich_hen_hom_nay = LichHen.objects.filter(ngay_hen=today).count()

  lich_hen_cho_duyet = LichHen.objects.filter(
      Q(trang_thai='CHO_DUYET')
      | Q(trang_thai='PENDING')
      | Q(trang_thai__icontains='chờ')
  ).count()

  # Tính doanh thu hôm nay
  tong_doanh_thu = (
      DichVuDaSuDung.objects.filter(
          ngay_su_dung__gte=now.replace(
              hour=0, minute=0, second=0, microsecond=0
          )
      ).aggregate(total=Sum('ma_dv__gia_dich_vu'))['total']
      or 0
  )
  doanh_thu_hom_nay = f'{tong_doanh_thu:,.0f}'.replace(',', '.')

  tong_khach_hang = KhachHang.objects.count()

  phan_hoi_cho_xu_ly = PhanHoiKhieuNai.objects.filter(
      Q(trang_thai_xu_ly='Đã tiếp nhận') | Q(trang_thai_xu_ly='Đang xử lý')
  ).count()

  yeu_cau_tu_van_cho = YeuCauTuVan.objects.filter(
      trang_thai='Chờ xử lý'
  ).count()

  uu_dai_dang_chay = ChuongTrinhUuDai.objects.filter(
      ngay_bat_dau__lte=now, ngay_ket_thuc__gte=now
  ).count()

  # 2. DỮ LIỆU BIỂU ĐỒ TĂNG TRƯỞNG 7 NGÀY
  chart_labels = []
  chart_data_bookings = []
  chart_data_revenue = []

  for i in range(6, -1, -1):
    day = today - timedelta(days=i)
    chart_labels.append(day.strftime('%d/%m'))

    cnt = LichHen.objects.filter(ngay_hen=day).count()
    chart_data_bookings.append(cnt)

    start_dt = timezone.make_aware(
        timezone.datetime.combine(day, timezone.datetime.min.time())
    )
    end_dt = timezone.make_aware(
        timezone.datetime.combine(day, timezone.datetime.max.time())
    )

    rev = (
        DichVuDaSuDung.objects.filter(
            ngay_su_dung__range=(start_dt, end_dt)
        ).aggregate(total=Sum('ma_dv__gia_dich_vu'))['total']
        or 0
    )
    chart_data_revenue.append(round(float(rev) / 1_000_000, 2))

    # 3. BIỂU ĐỒ TRÒN TOP DỊCH VỤ SỬ DỤNG
    top_services = (
        DichVuDaSuDung.objects.values('ma_dv__ten_dich_vu')
        .annotate(total=Count('ma_sd'))
        .order_by('-total')[:5]
    )

    pie_labels = [item['ma_dv__ten_dich_vu'] for item in top_services]
    pie_data = [item['total'] for item in top_services]

  # 4. DANH SÁCH CẦN X XỬ LÝ
  recent_bookings = (
      LichHen.objects.filter(ngay_hen=today)
      .select_related('ma_kh', 'ma_dv')
      .order_by('gio_hen')[:6]
  )

  recent_feedbacks = (
      PhanHoiKhieuNai.objects.filter(
          Q(trang_thai_xu_ly='Đã tiếp nhận') | Q(trang_thai_xu_ly='Đang xử lý')
      )
      .select_related('ma_kh', 'ma_dv')
      .order_by('-ngay_gui')[:4]
  )

  recent_chatbot_requests = (
      YeuCauTuVan.objects.filter(trang_thai='Chờ xử lý')
      .select_related('ma_pht')
      .order_by('-thoi_gian_yeu_cau')[:4]
  )

  context = {
      'active_menu': 'dashboard',
      'so_lich_hen_hom_nay': so_lich_hen_hom_nay,
      'lich_hen_cho_duyet': lich_hen_cho_duyet,
      'doanh_thu_hom_nay': doanh_thu_hom_nay,
      'tong_khach_hang': tong_khach_hang,
      'phan_hoi_cho_xu_ly': phan_hoi_cho_xu_ly,
      'yeu_cau_tu_van_cho': yeu_cau_tu_van_cho,
      'uu_dai_dang_chay': uu_dai_dang_chay,
      'chart_labels': chart_labels,
      'chart_data_bookings': chart_data_bookings,
      'chart_data_revenue': chart_data_revenue,
      'pie_labels': pie_labels,
      'pie_data': pie_data,
      'recent_bookings': recent_bookings,
      'recent_feedbacks': recent_feedbacks,
      'recent_chatbot_requests': recent_chatbot_requests,
  }
  return render(request, 'core/staff_dashboard.html', context)