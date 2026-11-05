
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('customer/', views.customer_home, name='customer_home'),
    path('staff/', views.staff_home, name='staff_home'),
    path("", views.home, name="home"),
    path('lieu_trinh/', views.lieu_trinh_page, name='lieu_trinh_page'),
    path('customer/profile/', views.customer_profile_view, name='customer_profile'),
    path('contact/', views.contact_view, name='contact'),
    path('khong-gian/', views.khong_gian_view, name='khong_gian'),
]
