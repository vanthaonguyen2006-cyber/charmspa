from django.urls import path

from . import views, views_chat, views_script

app_name = 'chatbot'

urlpatterns = [
    # --- APIs CHATBOT & LỊCH SỬ DÀNH CHO KHÁCH HÀNG ---
    path('api/chat/', views.chatbot_reply, name='chat_api'),
    path('api/chat/history/', views.chat_history, name='chat_history_api'),
    path('api/script/', views_script.script_graph_api, name='script_graph_api'),
    path('api/chat/me/', views_chat.chat_me, name='chat_me'),
    path('api/chat/flow/', views_chat.chat_flow, name='chat_flow'),
    path('api/chat/consult/', views_chat.chat_consult, name='chat_consult'),
    path('api/chat/state/', views_chat.chat_state, name='chat_state'),
    path('api/chat/send/', views_chat.chat_send, name='chat_send'),
    path('media/<str:name>', views_script.script_media, name='script_media'),
    path('history/', views.customer_chat_history, name='customer_history'),

    # --- CHATBOARD & APIs DÀNH CHO NHÂN VIÊN CSKH ---
    path('staff/', views.staff_chat_dashboard, name='staff_dashboard'),
    path('staff/api/sessions/', views.staff_get_sessions, name='staff_get_sessions'),
    path('staff/api/send/', views.staff_send_reply, name='staff_send_reply'),

    # --- QUẢN LÝ HỘI THOẠI CSKH (BÁO CÁO - ẢNH 2, 3, 4) ---
    path('admin/conversations/', views_chat.admin_conversation_list, name='admin_conversation_list'),
    path('admin/conversations/<str:session_id>/', views_chat.admin_conversation_detail, name='admin_conversation_detail'),
    path('admin/conversations/<str:session_id>/accept/', views_chat.admin_conversation_accept, name='admin_conversation_accept'),
    path('admin/conversations/<str:session_id>/reply/', views_chat.admin_conversation_reply, name='admin_conversation_reply'),
    path('admin/conversations/<str:session_id>/messages/', views_chat.admin_conversation_messages, name='admin_conversation_messages'),
    path('admin/conversations/<str:session_id>/complete/', views_chat.admin_conversation_complete, name='admin_conversation_complete'),

    # --- QUẢN LÝ KỊCH BẢN CHATBOT (BÁO CÁO - ẢNH 13, 14, 15, 16, 17) ---
    path('admin/scripts/', views.admin_script_list, name='admin_script_list'),
    path('admin/scripts/create/', views_script.admin_script_create, name='admin_script_create'),
    path('admin/scripts/upload-image/', views_script.admin_script_image_upload, name='admin_script_image_upload'),
    path('admin/scripts/<str:pk>/', views_script.admin_script_detail, name='admin_script_detail'),
    path('admin/scripts/<str:pk>/edit/', views_script.admin_script_edit, name='admin_script_edit'),
    path('admin/scripts/<str:pk>/graph/save/', views_script.admin_script_graph_save, name='admin_script_graph_save'),
    path('admin/scripts/<str:pk>/preview/', views_script.admin_script_preview, name='admin_script_preview'),
    path('admin/scripts/<str:pk>/delete/', views.admin_script_delete, name='admin_script_delete'),
    path('admin/scripts/<str:pk>/toggle/', views.admin_script_toggle_status, name='admin_script_toggle_status'),

    path('staff/api/messages/<str:session_id>/', views.get_conversation_messages_api, name='api_get_messages'),
]
