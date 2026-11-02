from django.urls import path
from . import views, ui_views

# Namespace dùng trong template: feedback:admin_feedback_list
app_name = "feedback"

urlpatterns = [
    # =========================
    # GIAO DIỆN KHÁCH HÀNG
    # Giữ nguyên các chức năng đã có
    # =========================
    path(
        "customer/create/",
        views.customer_feedback_create,
        name="customer_feedback_create",
    ),
    path(
        "customer/list/",
        views.customer_feedback_list,
        name="customer_feedback_list",
    ),
    path(
        "customer/<str:feedback_id>/",
        views.customer_feedback_detail,
        name="customer_feedback_detail",
    ),

    # =========================
    # GIAO DIỆN ADMIN
    # =========================

    # Danh sách tất cả phản hồi và khiếu nại
    path(
        "admin-ui/",
        ui_views.admin_feedback_list,
        name="admin_feedback_list",
    ),

    # Các danh sách riêng của admin
    path(
        "admin-ui/chua-phan-cong/",
        ui_views.admin_feedback_unassigned,
        name="admin_feedback_unassigned",
    ),
    path(
        "admin-ui/khong-hop-le/",
        ui_views.admin_feedback_invalid,
        name="admin_feedback_invalid",
    ),
    path(
        "admin-ui/thong-ke/",
        ui_views.admin_feedback_statistics,
        name="admin_feedback_statistics",
    ),

    # Chi tiết một phiếu của admin
    path(
        "admin-ui/<str:feedback_id>/",
        ui_views.admin_feedback_detail,
        name="admin_feedback_detail",
    ),

    # =========================
    # GIAO DIỆN NHÂN VIÊN
    # =========================

    # Danh sách phiếu được phân công
    path(
        "staff-ui/",
        ui_views.staff_feedback_list,
        name="staff_feedback_list",
    ),

    # Danh sách phiếu đã giải quyết
    path(
        "staff-ui/da-giai-quyet/",
        ui_views.staff_feedback_resolved,
        name="staff_feedback_resolved",
    ),

    # Chi tiết và xử lý một phiếu
    path(
        "staff-ui/<str:feedback_id>/",
        ui_views.staff_feedback_detail,
        name="staff_feedback_detail",
    ),
]