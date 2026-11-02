from django.shortcuts import render
from customers.models import KhachHang

def customer_home(request):
    return render(request, 'core/customer_home.html')

def staff_home(request):
    return render(request, 'core/staff_home.html')

# Hiển thị trang chủ Charm Spa Grand
def home(request):
    return render(request, "core/home.html")