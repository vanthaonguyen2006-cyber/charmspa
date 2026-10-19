from django.urls import path
from . import views

urlpatterns = [
    path('customer/', views.customer_home, name='customer_home'),
    # Các đường dẫn khác của bạn...
    path('customer/profile/', views.customer_profile_view, name='customer_profile'),
]