from django.urls import path
from . import views

urlpatterns = [
    path('customer/', views.customer_home, name='customer_home'),
    # Các đường dẫna khác của bạn...

]