from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('customer/', views.customer_home, name='customer_home'),
    # Các đường dẫn khác của bạn...
    path('customer/profile/', views.customer_profile_view, name='customer_profile'),
    path('contact/', views.contact_view, name='contact'),
]