
from django.urls import path
from . import views

urlpatterns = [
    path('customer/', views.customer_home, name='customer_home'),
    path('staff/', views.staff_home, name='staff_home'),
    path('lieu_trinh/', views.lieu_trinh_page, name='lieu_trinh_page'),
]
