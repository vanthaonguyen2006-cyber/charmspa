from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    # APIs cho Khách hàng
    path('api/chat/', views.chatbot_reply, name='chatbot_reply'),
    path('api/chat/history/', views.chat_history, name='chat_history'),

    # Live Chat Dashboard cho Nhân viên CSKH
    path('staff/', views.staff_chat_dashboard, name='staff_dashboard'),
    path('api/staff/reply/', views.staff_send_reply, name='staff_send_reply'),
    path('api/staff/sessions/', views.staff_get_sessions, name='staff_get_sessions'),  # Thêm đường dẫn này
]