from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # ------------------------------------------------------------------
    # 1. TRUNG TÂM THÔNG BÁO KHÁCH HÀNG (TRANG CÁ NHÂN)
    # ------------------------------------------------------------------
    path('', views.danh_sach_thong_bao, name='danh_sach_thong_bao'),
    path('customer/', views.danh_sach_thong_bao, name='customer_notification_center'),
    path('read/<str:ma_tbkh>/', views.danh_dau_da_doc, name='danh_dau_da_doc'),

    # ------------------------------------------------------------------
    # 2. MODULE ƯU ĐÃI (PROMOTIONS)
    # ------------------------------------------------------------------
    path('promotions/', views.danh_sach_uu_dai, name='danh_sach_uu_dai'),
    path('promotions/detail/<str:promo_code>/', views.chi_tiet_uu_dai, name='chi_tiet_uu_dai'),
    path('promotions/detail/<str:promo_code>/', views.chi_tiet_uu_dai, name='promotion_detail'), # Hỗ trợ cả 2 tên gọi

    # Admin Promotions
    path('promotions/admin/', views.admin_promotion_list, name='admin_promotion_list'),
    path('promotions/add/', views.them_uu_dai, name='them_uu_dai'),
    path('promotions/save/', views.api_them_hoac_sua_uu_dai, name='api_them_hoac_sua_uu_dai'),
    path('promotions/edit/<str:ma_ctud>/', views.chinh_sua_uu_dai, name='chinh_sua_uu_dai'),
    path('promotions/get-detail/<str:ma_ctud>/', views.get_promotion_detail, name='get_promotion_detail'),
    path('promotions/delete/<str:ma_ctud>/', views.xoa_uu_dai, name='xoa_uu_dai'),
    path('promotions/api-send/', views.api_gui_thong_bao_uu_dai, name='api_gui_thong_bao_uu_dai'), # Bổ sung API gửi thông báo

    # ------------------------------------------------------------------
    # 3. MODULE CHĂM SÓC SAU LIỆU TRÌNH (AFTERCARE - ADMIN & CUSTOMER)
    # ------------------------------------------------------------------
    path('post-treatment/', views.cham_soc_sau_lieu_trinh, name='cham_soc_sau_lieu_trinh'),
    path('post-treatment/send/<int:id>/', views.gui_hdcs_action, name='gui_hdcs_action'),
    path('post-treatment/detail-json/<int:id>/', views.get_hdcs_detail, name='get_hdcs_detail'),

    path('schedules/', views.lich_hen_chu_ky_cham_soc, name='lich_hen_chu_ky_cham_soc'),
    path('rebook/', views.dat_lich_tai_hen_nhanh, name='dat_lich_tai_hen_nhanh'),
]