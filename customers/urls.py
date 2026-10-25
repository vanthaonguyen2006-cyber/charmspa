from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    # Trỏ đường dẫn /customer/profile/ tới hàm có sẵn trong views.py của bạn
    path('', views.customer_home_view, name='customer_home'),
    path('profile/', views.customer_profile_view, name='customer_profile'),
]