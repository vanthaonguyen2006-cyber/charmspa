from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/customer/', permanent=False)), # Tự điều hướng / sang /customer/
    path('admin/', admin.site.urls),
    path('feedback/', include('feedback.urls')),
    path('customer/', include('customers.urls')),
    path('home/', include('core.urls')),
    path('chatbot/', include('chatbot.urls')),
    path('accounts/', include('accounts.urls')),
    path('bookings/', include('bookings.urls')),
]