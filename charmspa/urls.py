from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('feedback/', include('feedback.urls')),
    path('customer/', include('customers.urls')),
    path('home/', include('core.urls')),
    path('bookings/', include('bookings.urls')),
]