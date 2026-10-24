from django.shortcuts import render
from customers.models import KhachHang

def customer_home(request):
    return render(request, 'core/customer_home.html')


